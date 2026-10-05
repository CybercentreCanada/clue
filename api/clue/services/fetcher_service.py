from time import monotonic
from typing import Any
from urllib.parse import urljoin

import requests
from elasticapm.traces import capture_span
from flask import request
from pydantic import TypeAdapter, ValidationError
from requests import JSONDecodeError, exceptions

from clue.common.exceptions import (
    AuthenticationException,
    ClueException,
    ClueValueError,
    InvalidDataException,
    NotFoundException,
)
from clue.common.logging import get_logger
from clue.config import CLASSIFICATION, config
from clue.helper.headers import generate_headers
from clue.helper.obo import get_obo_access_token
from clue.helper.plugin_requests import quote_plugin_path_segment, request_with_safe_redirects
from clue.models.config import ExternalSource
from clue.models.fetchers import FetcherDefinition, FetcherResult
from clue.models.selector import Selector
from clue.models.validators import validate_plugin_identifier

logger = get_logger(__file__)


def _raise_fetcher_metadata_unavailable(error: Exception | None = None) -> None:
    raise ClueException(
        "Unable to verify fetcher availability with the upstream source.", error, status_code=503
    ) from error


def get_supported_fetchers(
    source: ExternalSource,
    headers: dict[str, str],
    *,
    timeout: float = 5.0,
    raise_on_error: bool = False,
) -> dict[str, FetcherDefinition]:
    """Fetch current metadata without caching authorization classifications.

    Args:
        source (ExternalSource): The source whose fetchers to retrieve.
        headers (dict[str, str]): Headers to include in the upstream request.
        timeout (float): The upstream request timeout in seconds.
        raise_on_error (bool): Raise a 503 when metadata cannot be verified.

    Returns:
        dict[str, FetcherDefinition]: A dict of each ids mapped to fetcher metadata
    """
    logger.info("Requesting fetchers for source %s", source.name)

    url = urljoin(source.url, "fetchers/")

    with capture_span(f"GET {url}", span_type="http"):
        try:
            rsp = request_with_safe_redirects(requests.get, url, headers=headers, timeout=timeout)
            result = rsp.json()

            if not rsp.ok:
                err = result["api_error_message"]
                logger.error(f"Error from upstream server: {rsp.status_code=}, {err=}")
                if raise_on_error:
                    _raise_fetcher_metadata_unavailable()
                return {}

            fetchers = TypeAdapter(dict[str, FetcherDefinition]).validate_python(result["api_response"])
            for identifier in fetchers:
                validate_plugin_identifier(identifier)
            return fetchers
        except (ClueValueError, ValidationError) as err:
            logger.warning("Invalid fetcher metadata from %s", source.name)
            if raise_on_error:
                _raise_fetcher_metadata_unavailable(err)
            return {}
        except ClueException:
            raise
        except Exception as err:
            logger.exception("Unable to retrieve fetcher metadata from %s", source.url)
            if raise_on_error:
                _raise_fetcher_metadata_unavailable(err)
            return {}


def all_supported_fetchers(user: dict[str, Any]) -> dict[str, FetcherDefinition]:
    """Gets all supported fetchers for all sources

    Args:
        user (dict[str, Any]): The user requesting the fetchers.

    Returns:
        dict[str, FetcherDefinition]: A dict of all fetchers and their matching schema
    """
    all_fetchers: dict[str, FetcherDefinition] = {}

    for source in config.api.external_sources:
        if not CLASSIFICATION.is_accessible(user["classification"], source.classification):
            continue

        try:
            access_token, obo_access_token = get_obo_access_token(source, user)
        except AuthenticationException:
            continue

        supported_fetchers = get_supported_fetchers(
            source, generate_headers(obo_access_token=obo_access_token, access_token=access_token)
        )
        total_fetchers = 0
        for key, action in supported_fetchers.items():
            total_fetchers += 1
            all_fetchers[f"{source.name}.{key}"] = action
        logger.debug("Plugin %s exposes %s fetcher(s)", source.name, total_fetchers)

    return all_fetchers


def get_plugins_supported_fetchers(user: dict[str, Any]) -> dict[str, FetcherDefinition]:
    """Return the supported fetchers of each external service, filtered to what the user has access to."""
    available_fetchers: dict[str, FetcherDefinition] = {}

    all_fetchers = all_supported_fetchers(user)

    logger.info("Retrieving fetchers for classification %s", user["classification"])

    for fetcher_id, fetcher in all_fetchers.items():
        # Validate if the user is allow to even see the source
        if user and not CLASSIFICATION.is_accessible(user["classification"], fetcher.classification):
            logger.info(
                "Not including fetchers from source %s at classification %s", fetcher.id, user["classification"]
            )
            continue

        # user can view source, now filter types user cannot see
        available_fetchers[fetcher_id] = fetcher

    logger.info("%s fetchers are available for user %s", len(available_fetchers), user["uname"])

    return available_fetchers


def _validate_fetcher_classification(fetcher: FetcherDefinition | None, selector: Selector, fetcher_id: str) -> None:
    if fetcher and not CLASSIFICATION.is_accessible(fetcher.classification, selector.classification):
        raise InvalidDataException(
            f"Cannot send data classified as {selector.classification} to fetcher {fetcher_id} "
            f"at classification {fetcher.classification}.",
            status_code=400,
        )


def run_fetcher(plugin_id: str, fetcher_id: str, user: dict[str, Any]) -> FetcherResult:
    """Executes a specified fetcher.

    Args:
        plugin_id (str): The ID of the plugin.
        fetcher_id (str): The ID of the action to run.
        user (dict[str, Any]): The user dict of the user running the action.

    Raises:
        NotFoundException: Raised whenever the plugin or the action doesn't exist.
        ClueException: Raised whenever an error is returned by the plugin endpoint.

    Returns:
        ActionResult: The result of the action.
    """
    validate_plugin_identifier(fetcher_id)
    plugin = next((source for source in config.api.external_sources if source.name == plugin_id), None)

    if not plugin or not CLASSIFICATION.is_accessible(user["classification"], plugin.classification):
        raise NotFoundException("Fetcher not found.", status_code=404)

    access_token, obo_access_token = get_obo_access_token(plugin, user)

    headers = generate_headers(obo_access_token=obo_access_token, access_token=access_token)

    if request.is_json:
        parameters = request.json
    else:
        logger.error(
            "Invalid content-type detected: %s",
        )
        raise ClueValueError(
            "The request body must be of type application/json.",
            status_code=400,
        )

    try:
        selector = Selector.model_validate(parameters)
        supported_fetchers = get_supported_fetchers(plugin, headers)

        fetcher = supported_fetchers.get(fetcher_id)
        if fetcher is None or not CLASSIFICATION.is_accessible(user["classification"], fetcher.classification):
            raise NotFoundException("Fetcher not found.", status_code=404)
        _validate_fetcher_classification(fetcher, selector, fetcher_id)

        response = request_with_safe_redirects(
            requests.post,
            urljoin(plugin.url, f"fetchers/{quote_plugin_path_segment(fetcher_id)}"),
            get_method=requests.get,
            json=parameters,
            headers=headers,
            timeout=request.args.get("max_timeout", 60.0, type=float),
        )

        result = response.json()

        if not response.ok:
            raise ClueException(
                result["api_error_message"] or result["api_response"].get("error", ""), status_code=response.status_code
            )

        return FetcherResult.model_validate(result["api_response"], context={"is_response": True})
    except ValidationError as err:
        logger.exception("Invalid Request Body:")
        raise InvalidDataException(
            "Validation error encountered on request body. Ensure your request body is properly formatted.",
            status_code=400,
        ) from err
    except (JSONDecodeError, exceptions.ConnectionError, exceptions.Timeout) as err:
        logger.exception(f"Something went wrong when running fetcher from plugin '{plugin_id}'")
        raise ClueException(
            f"Something went wrong when running fetcher from plugin '{plugin_id}': {err.__class__.__name__}."
        ) from err


def get_fetcher_status(plugin_id: str, fetcher_id: str, task_id: str, user: dict[str, Any]) -> FetcherResult:
    """Executes a specified fetcher.

    Args:
        plugin_id (str): The ID of the plugin.
        fetcher_id (str): The ID of the action to run.
        task_id (str): The task id to fetch the status for
        user (dict[str, Any]): The user dict of the user running the action.

    Raises:
        NotFoundException: Raised whenever the plugin or the action doesn't exist.
        ClueException: Raised whenever an error is returned by the plugin endpoint.

    Returns:
        ActionResult: The result of the action.
    """
    validate_plugin_identifier(fetcher_id)
    validate_plugin_identifier(task_id)
    plugin = next((source for source in config.api.external_sources if source.name == plugin_id), None)

    if not plugin or not CLASSIFICATION.is_accessible(user["classification"], plugin.classification):
        raise NotFoundException("Fetcher not found.", status_code=404)

    access_token, obo_access_token = get_obo_access_token(plugin, user)

    headers = generate_headers(obo_access_token=obo_access_token, access_token=access_token)

    timeout = request.args.get("max_timeout", 60.0, type=float)
    metadata_started = monotonic()
    # Authorization metadata must stay fresh; include this lookup in the caller's timeout budget.
    fetcher = get_supported_fetchers(
        plugin,
        headers,
        timeout=max(min(timeout, 5.0), 0.001),
        raise_on_error=True,
    ).get(fetcher_id)
    if fetcher is None or not CLASSIFICATION.is_accessible(user["classification"], fetcher.classification):
        raise NotFoundException("Fetcher not found.", status_code=404)

    remaining_timeout = max(timeout - (monotonic() - metadata_started), 0.001)

    try:
        req_url = urljoin(
            plugin.url, f"fetchers/{quote_plugin_path_segment(fetcher_id)}/status/{quote_plugin_path_segment(task_id)}"
        )
        logger.debug("Getting status for action %s with task_id %s for user %s", req_url, task_id, user["uname"])

        response = request_with_safe_redirects(
            requests.get,
            req_url,
            headers=headers,
            timeout=remaining_timeout,
        )

        result = response.json()

        if not response.ok:
            raise ClueException(
                result["api_error_message"] or result["api_response"].get("error", ""), status_code=response.status_code
            )

        return FetcherResult.model_validate(result["api_response"], context={"is_response": True})
    except ValidationError as err:
        logger.exception("Invalid Request Body:")
        raise ClueValueError(
            "Validation error encountered on response body.",
            status_code=400,
        ) from err
    except (JSONDecodeError, exceptions.ConnectionError, exceptions.Timeout) as err:
        logger.exception(f"Something went wrong when getting the status of the fetcher from plugin '{plugin_id}'")
        raise ClueException(
            f"Something went wrong getting the status of fetcher from plugin '{plugin_id}': {err.__class__.__name__}."
        ) from err
