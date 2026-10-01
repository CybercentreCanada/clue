from time import monotonic
from typing import Any
from urllib.parse import urljoin

import requests
from elasticapm.traces import capture_span
from flask import request
from pydantic import TypeAdapter
from requests import JSONDecodeError, exceptions

from clue.common.exceptions import AuthenticationException, ClueException, NotFoundException
from clue.common.logging import get_logger
from clue.config import CLASSIFICATION, config
from clue.helper.headers import generate_headers
from clue.helper.obo import get_obo_access_token
from clue.helper.plugin_requests import request_with_safe_redirects
from clue.models.actions import ActionResult, ActionSpec
from clue.models.config import ExternalSource

logger = get_logger(__file__)


def _raise_action_metadata_unavailable(error: Exception | None = None) -> None:
    raise ClueException(
        "Unable to verify action availability with the upstream source.", error, status_code=503
    ) from error


def get_supported_actions(
    source: ExternalSource,
    headers: dict[str, str],
    *,
    timeout: float = 10.0,
    raise_on_error: bool = False,
) -> dict[str, ActionSpec]:
    """Gets all supported actions for a source

    Args:
        source (ExternalSource): The source whose actions to retrieve.
        access_token (Optional[str]): The caller's access token, if available.
        obo_access_token (Optional[str]): The source-specific OBO token, if available.
        timeout (float): The upstream request timeout in seconds.
        raise_on_error (bool): Raise a 503 when metadata cannot be verified.

    Returns:
        dict[str, ActionSpec]: A dict of each action and their schema
    """
    return _get_supported_actions(source, headers, timeout=timeout, raise_on_error=raise_on_error)


def _get_supported_actions(
    source: ExternalSource,
    headers: dict[str, str],
    *,
    timeout: float,
    raise_on_error: bool,
) -> dict[str, ActionSpec]:
    """Fetch current metadata for listing and authorization without caching classifications."""
    logger.info("Fetching actions for source %s", source.name)
    url = urljoin(source.url, "actions/")

    with capture_span(f"GET {url}", span_type="http"):
        rsp = None
        try:
            rsp = request_with_safe_redirects(requests.get, url, headers=headers, timeout=timeout)
            result = rsp.json()

            if not rsp.ok:
                err = result["api_error_message"]
                logger.error(f"Error from upstream server: {rsp.status_code=}, {err=}")
                if raise_on_error:
                    _raise_action_metadata_unavailable()
                return {}

            return TypeAdapter(dict[str, ActionSpec]).validate_python(result["api_response"])
        except ClueException:
            raise
        except Exception as err:
            logger.exception("Unable to retrieve action metadata from %s", source.url)
            if raise_on_error:
                _raise_action_metadata_unavailable(err)
            return {}


def all_supported_actions(user: dict[str, Any]) -> dict[str, ActionSpec]:
    """Gets all supported actions for all sources

    Args:
        access_token (Optional[str], optional): The access token to use, if necessary. Defaults to None.

    Returns:
        dict[str, ActionSpec]: A dict of all actions and their matching schema
    """
    all_actions: dict[str, ActionSpec] = {}

    for source in config.api.external_sources:
        if not CLASSIFICATION.is_accessible(user["classification"], source.classification):
            continue

        try:
            access_token, obo_access_token = get_obo_access_token(source, user)
        except AuthenticationException:
            continue

        supported_actions = get_supported_actions(
            source, generate_headers(obo_access_token=obo_access_token, access_token=access_token)
        )
        total_actions = 0
        for key, action in supported_actions.items():
            total_actions += 1
            all_actions[f"{source.name}.{key}"] = action
        logger.debug("Plugin %s exposes %s action(s)", source.name, total_actions)

    return all_actions


def get_plugins_supported_actions(user: dict[str, Any]) -> dict[str, ActionSpec]:
    """Return the supported actions of each external service, filtered to what the user has access to."""
    available_actions: dict[str, ActionSpec] = {}

    all_actions = all_supported_actions(user)

    logger.info("Fetching actions for classification %s", user["classification"])

    for action_id, action in all_actions.items():
        # Validate if the user is allow to even see the source
        if user and not CLASSIFICATION.is_accessible(user["classification"], action.classification):
            logger.info(
                "Not including actions from source %s at classification %s", action.name, user["classification"]
            )
            continue

        # user can view source, now filter types user cannot see
        available_actions[action_id] = action

    logger.info("%s actions are available for user %s", len(available_actions), user["uname"])

    return available_actions


def execute_action(plugin_id: str, action_id: str, user: dict[str, Any]) -> ActionResult:
    """Executes a specified action.

    Args:
        plugin_id (str): The ID of the plugin.
        action_id (str): The ID of the action to run.
        user (dict[str, Any]): The user dict of the user running the action.

    Raises:
        NotFoundException: Raised whenever the plugin or the action doesn't exist.
        ClueException: Raised whenever an error is returned by the plugin endpoint.

    Returns:
        ActionResult: The result of the action.
    """
    plugin = next((source for source in config.api.external_sources if source.name == plugin_id), None)

    if not plugin or not CLASSIFICATION.is_accessible(user["classification"], plugin.classification):
        raise NotFoundException("Action not found.", status_code=404)

    try:
        access_token, obo_access_token = get_obo_access_token(plugin, user)
    except AuthenticationException:
        return ActionResult(outcome="failure", summary="Invalid token provided for this enrichment.")

    headers = generate_headers(obo_access_token=obo_access_token, access_token=access_token)

    action = get_supported_actions(plugin, headers).get(action_id)
    if action is None or not CLASSIFICATION.is_accessible(user["classification"], action.classification):
        raise NotFoundException("Action not found.", status_code=404)

    if request.content_type == "application/json":
        parameters = request.json
    else:
        # TODO: Pass parameters via urlencode?
        parameters = {}

    try:
        req_url = urljoin(plugin.url, f"actions/{action_id}")
        logger.debug("Executing action %s for user %s", req_url, user["uname"])

        response = request_with_safe_redirects(
            requests.post,
            req_url,
            get_method=requests.get,
            json=parameters,
            headers=headers,
            timeout=request.args.get("max_timeout", plugin.default_timeout, type=float),
        )

        result = response.json()

        if not response.ok:
            raise ClueException(result["api_error_message"])

        return ActionResult.model_validate(result["api_response"], context={"is_response": True})
    except (JSONDecodeError, exceptions.ConnectionError, exceptions.Timeout) as err:
        logger.exception(f"Something went wrong when retrieving the result from plugin '{plugin_id}'")
        raise ClueException(
            f"Something went wrong when retrieving the result from plugin '{plugin_id}': {err.__class__.__name__}."
        )


def get_action_status(plugin_id: str, action_id: str, task_id: str, user: dict[str, Any]) -> ActionResult:
    """Gets the status of a specified action with task_id.

    Args:
        plugin_id (str): The ID of the plugin.
        action_id (str): The ID of the action to run.
        task_id (str): The task id to fetch the status for
        user (dict[str, Any]): The user dict of the user running the action.

    Raises:
        NotFoundException: Raised whenever the plugin or the action doesn't exist.
        ClueException: Raised whenever an error is returned by the plugin endpoint.

    Returns:
        ActionResult: The result of the action.
    """
    plugin = next((source for source in config.api.external_sources if source.name == plugin_id), None)

    if not plugin or not CLASSIFICATION.is_accessible(user["classification"], plugin.classification):
        raise NotFoundException("Action not found.", status_code=404)

    try:
        access_token, obo_access_token = get_obo_access_token(plugin, user)
    except AuthenticationException:
        return ActionResult(outcome="failure", summary="Invalid token provided.")

    headers = generate_headers(obo_access_token=obo_access_token, access_token=access_token)

    timeout = request.args.get("max_timeout", plugin.default_timeout, type=float)
    metadata_started = monotonic()
    # Authorization metadata must stay fresh; include this lookup in the caller's timeout budget.
    action = get_supported_actions(
        plugin,
        headers,
        timeout=max(min(timeout, 10.0), 0.001),
        raise_on_error=True,
    ).get(action_id)
    if action is None or not CLASSIFICATION.is_accessible(user["classification"], action.classification):
        raise NotFoundException("Action not found.", status_code=404)

    remaining_timeout = max(timeout - (monotonic() - metadata_started), 0.001)

    try:
        req_url = urljoin(plugin.url, f"actions/{action_id}/status/{task_id}")
        logger.debug("Getting status for action %s with task_id %s for user %s", req_url, task_id, user["uname"])

        response = request_with_safe_redirects(
            requests.get,
            req_url,
            headers=headers,
            timeout=remaining_timeout,
        )

        result = response.json()

        if not response.ok:
            raise ClueException(result["api_error_message"])

        return ActionResult.model_validate(result["api_response"], context={"is_response": True})
    except (JSONDecodeError, exceptions.ConnectionError, exceptions.Timeout) as err:
        logger.exception(f"Something went wrong when retrieving the status from plugin '{plugin_id}'")
        raise ClueException(
            f"Something went wrong when retrieving the status from plugin '{plugin_id}': {err.__class__.__name__}."
        )
