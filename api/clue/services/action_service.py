from typing import Any, Optional
from urllib.parse import urljoin

import elasticapm
import requests
from flask import request
from pydantic import TypeAdapter, ValidationError
from requests import JSONDecodeError, exceptions

from clue.common.exceptions import ClueException, NotFoundException
from clue.common.logging import get_logger
from clue.config import CLASSIFICATION, config
from clue.helper.headers import generate_headers
from clue.models.actions import ActionResult, ActionSpec
from clue.models.config import ExternalSource
from clue.services import auth_service

logger = get_logger(__file__)


def get_supported_actions(
    source: ExternalSource, user: dict[str, Any], access_token: Optional[str] = None
) -> dict[str, ActionSpec]:
    """Gets all supported actions for a source

    Args:
        source_url (str): The URL of the source
        access_token (Optional[str], optional): The access token to use, if necessary. Defaults to None.

    Returns:
        dict[str, ActionSpec]: A dict of each action and their schema
    """
    logger.info("Fetching actions for source %s", source.name)

    url = urljoin(source.url, "actions/")

    obo_access_token = None
    if access_token:
        obo_access_token, error = auth_service.check_obo(source, access_token, user["uname"])

        if error:
            logger.error("%s: %s", source.name, error)
            return {}

    headers = generate_headers(obo_access_token or access_token, access_token if obo_access_token else None)

    with elasticapm.capture_span(f"GET {url}", span_type="http"):
        try:
            rsp = requests.get(url, headers=headers, timeout=10.0)
            result = rsp.json()

            if not rsp.ok:
                err = result["api_error_message"]
                logger.error(f"Error from upstream server: {rsp.status_code=}, {err=}")

            return TypeAdapter(dict[str, ActionSpec]).validate_python(result["api_response"])
        except exceptions.ConnectionError:
            # any errors are logged and no result is saved to local cache to enable retry on next query
            logger.exception("Unable to connect: %s", url)
            return {}
        except (requests.exceptions.JSONDecodeError, KeyError, JSONDecodeError):
            logger.exception("External API did not return expected format. Full data:\n\n%s\n\nStack Trace:", rsp.text)
            return {}
        except ValidationError:
            logger.exception("ValidationError in response from %s:\n%s", source.url)
            return {}
        except Exception:
            logger.exception("Unknown exception occurred on action fetching:")
            return {}


def all_supported_actions(user: dict[str, Any], access_token: Optional[str] = None) -> dict[str, ActionSpec]:
    """Gets all supported actions for all sources

    Args:
        access_token (Optional[str], optional): The access token to use, if necessary. Defaults to None.

    Returns:
        dict[str, ActionSpec]: A dict of all actions and their matching schema
    """
    all_actions: dict[str, ActionSpec] = {}

    for source in config.api.external_sources:
        supported_actions = get_supported_actions(source, user, access_token=access_token)
        total_actions = 0
        for key, action in supported_actions.items():
            total_actions += 1
            all_actions[f"{source.name}.{key}"] = action
        logger.debug("Plugin %s exposes %s action(s)", source.name, total_actions)

    return all_actions


def get_plugins_supported_actions(user: dict[str, Any]) -> dict[str, ActionSpec]:
    """Return the supported actions of each external service, filtered to what the user has access to."""
    available_actions: dict[str, ActionSpec] = {}

    access_token = request.headers.get("Authorization", type=str)
    if access_token:
        access_token = access_token.split(" ")[1]

    all_actions = all_supported_actions(
        user,
        access_token=access_token,
    )

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
            return ActionResult(outcome="failure", summary="Invalid token provided for this enrichment.")

    headers = generate_headers(obo_access_token or access_token, access_token if obo_access_token else None)

    if request.content_type == "application/json":
        parameters = request.json
    else:
        # TODO: Pass parameters via urlencode?
        parameters = {}

    try:
        req_url = urljoin(plugin.url, f"actions/{action_id}")
        logger.debug("Executing action %s for user %s", req_url, user["uname"])

        response = requests.post(
            req_url,
            json=parameters,
            headers=headers,
            timeout=request.args.get("max_timeout", plugin.default_timeout, type=float),
        )

        result = response.json()

        if not response.ok:
            raise ClueException(result["api_error_message"])

        return ActionResult.model_validate(result["api_response"])
    except (JSONDecodeError, exceptions.ConnectionError) as err:
        logger.exception(f"Something went wrong when retrieving the result from plugin '{plugin_id}'")
        raise ClueException(
            f"Something went wrong when retrieving the result from plugin '{plugin_id}': {err.__class__.__name__}."
        )
