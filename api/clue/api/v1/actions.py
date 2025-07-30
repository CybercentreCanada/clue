"""Enrichment Actions

List and execute actions

* Provide endpoints to list valid actions exposed by plugins.
* Provide endpoints to execute these actions.
"""

from flask_cors import CORS

from clue.api import internal_error, make_subapi_blueprint, not_found, ok
from clue.common.exceptions import ClueException, NotFoundException
from clue.common.logging import get_logger
from clue.common.swagger import generate_swagger_docs
from clue.config import config
from clue.models.actions import Action, ActionResult
from clue.security import api_login
from clue.services import action_service

logger = get_logger(__file__)


SUB_API = "actions"
actions_api = make_subapi_blueprint(SUB_API, api_version=1)
actions_api._doc = "Run actions on data through configured external data sources/systems."

CORS(actions_api, origins=config.ui.cors_origins, supports_credentials=True)


@generate_swagger_docs(responses={200: "A list of types and their classification"})
@actions_api.route("/", methods=["GET"])
@api_login()
def get_actions(**kwargs) -> dict[str, Action]:
    """Return the supported actions of each external service.

    Variables:
    None

    Arguments:
    None

    Result Example:
    { # A dictionary of sources with their supported actions.
        <source_id>.<action_id>: {
            "id": "",
            "name": "",
            "classification": "",
            "summary": "",
            "supported_types": "",
            "params": {
                <JSON schema>
            }
        },
        ...,
    }
    """
    return ok(action_service.get_plugins_supported_actions(kwargs["user"]))


@generate_swagger_docs(responses={200: "Successful lookup to selected plugins"})
@actions_api.route("/execute/<plugin_id>/<action_id>", methods=["POST"])
@api_login()
def execute_action(plugin_id: str, action_id: str, **kwargs) -> ActionResult:
    """Search other services for additional information related to the provided data.

    Variables:
    plugin_id (str): the ID of the plugin who owns the action to execute
    action_id (str): the ID of the action to execute

    Arguments:
    None

    Data Block:
    {
        type: "ip",
        value: "127.0.0.1",
        ...
    }

    Result Example:
    {
        "outcome": "success | failure", # was this execution a success or failure?
        "format": "link", # What format is the output in?
        "output": "http://example.com" # The output of the action. Can be any data structure.
    }
    """
    try:
        return ok(action_service.execute_action(plugin_id, action_id, kwargs["user"]))
    except NotFoundException as err:
        return not_found(err=err.message)
    except ClueException as err:
        return internal_error(err=err.message)
