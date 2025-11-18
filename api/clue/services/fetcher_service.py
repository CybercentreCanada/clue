from typing import Any, Optional
from urllib.parse import urljoin

import elasticapm
import requests
from flask import request
from pydantic import TypeAdapter, ValidationError
from requests import JSONDecodeError, exceptions

from clue.common.exceptions import (
    AuthenticationException,
    ClueException,
    ClueValueError,
    NotFoundException,
)
from clue.common.logging import get_logger
from clue.config import CLASSIFICATION, DEBUG, cache, config
from clue.models.config import ExternalSource
from clue.models.fetchers import FetcherDefinition, FetcherResult
from clue.models.selector import Selector
from clue.services import auth_service

logger = get_logger(__file__)

# Either cache for one second in debug mode, or five minutes in production
CACHE_TIMEOUT: int = 1 if DEBUG else 5 * 60


@cache.memoize(timeout=1 if DEBUG else 5 * 60, args_to_ignore=["access_token"])  # Cached for 5 minutes
def get_supported_fetchers(
    source: ExternalSource, user: dict[str, Any], access_token: Optional[str] = None
) -> dict[str, FetcherDefinition]:
    """Gets all supported fetchers for a source

    Args:
        source_url (str): The URL of the source
        access_token (Optional[str], optional): The access token to use, if necessary. Defaults to None.

    Returns:
        dict[str, FetcherDefinition]: A dict of each ids mapped to fetcher metadata
    """
    logger.info("Requesting fetchers for source %s", source.name)

    url = urljoin(source.url, "fetchers/")

    obo_access_token = None
    if access_token:
        obo_access_token, error = auth_service.check_obo(source, access_token, user["uname"])

        if error:
            logger.error("%s: %s", source.name, error)
            return {}

    headers = {"Accept": "application/json"}
    if obo_access_token or access_token:
        headers["Authorization"] = f"Bearer {obo_access_token or access_token}"

    with elasticapm.capture_span(f"GET {url}", span_type="http"):
        try:
            rsp = requests.get(url, headers=headers, timeout=5.0)
            result = rsp.json()

            if not rsp.ok:
                err = result["api_error_message"]
                logger.error(f"Error from upstream server: {rsp.status_code=}, {err=}")

            return TypeAdapter(dict[str, FetcherDefinition]).validate_python(result["api_response"])
        except exceptions.ConnectionError:
            # any errors are logged and no result is saved to local cache to enable retry on next query
            logger.exception("Unable to connect: %s", url)
            return {}
        except (requests.exceptions.JSONDecodeError, KeyError):
            logger.exception("External API did not return expected format:")
            return {}
        except ValidationError:
            logger.exception("ValidationError in response from %s:", source.url)
            return {}


def all_supported_fetchers(user: dict[str, Any], access_token: Optional[str] = None) -> dict[str, FetcherDefinition]:
    """Gets all supported fetchers for all sources

    Args:
        access_token (Optional[str], optional): The access token to use, if necessary. Defaults to None.

    Returns:
        dict[str, FetcherDefinition]: A dict of all fetchers and their matching schema
    """
    all_fetchers: dict[str, FetcherDefinition] = {}

    for source in config.api.external_sources:
        supported_fetchers = get_supported_fetchers(source, user, access_token=access_token)
        total_fetchers = 0
        for key, action in supported_fetchers.items():
            total_fetchers += 1
            all_fetchers[f"{source.name}.{key}"] = action
        logger.debug("Plugin %s exposes %s fetcher(s)", source.name, total_fetchers)

    return all_fetchers


def get_plugins_supported_fetchers(user: dict[str, Any]) -> dict[str, FetcherDefinition]:
    """Return the supported fetchers of each external service, filtered to what the user has access to."""
    available_fetchers: dict[str, FetcherDefinition] = {}

    access_token = request.headers.get("Authorization", type=str)
    if access_token:
        access_token = access_token.split(" ")[1]

    all_fetchers = all_supported_fetchers(
        user,
        access_token=access_token,
    )

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
    plugin = next((source for source in config.api.external_sources if source.name == plugin_id), None)

    if not plugin:
        raise NotFoundException(f"Plugin {plugin_id} does not exist.")

    access_token = request.headers.get("Authorization", type=str)
    if access_token:
        access_token = access_token.split(" ")[1]

    obo_access_token = None
    if access_token:
        obo_access_token, error = auth_service.check_obo(plugin, access_token, user["uname"])

        if error:
            logger.error("%s: %s", plugin.name, error)
            raise AuthenticationException("Invalid token provided for this enrichment.")

    headers = {"Accept": "application/json"}
    if obo_access_token or access_token:
        headers["Authorization"] = f"Bearer {obo_access_token or access_token}"

    if request.content_type == "application/json":
        parameters = request.json
    else:
        # TODO: Pass parameters via urlencode?
        parameters = {}

    try:
        Selector.model_validate(parameters)

        response = requests.post(
            urljoin(plugin.url, f"fetchers/{fetcher_id}"),
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
        raise ClueValueError(
            "Validation error encountered on request body. Ensure your request body is properly formatted.",
            status_code=400,
        ) from err
    except (JSONDecodeError, exceptions.ConnectionError) as err:
        logger.exception(f"Something went wrong when running fetcher from plugin '{plugin_id}'")
        raise ClueException(
            f"Something went wrong when running fetcher from plugin '{plugin_id}': {err.__class__.__name__}."
        ) from err
