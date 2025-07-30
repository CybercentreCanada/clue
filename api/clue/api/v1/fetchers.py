"""Enrichment Fetchers

List and execute fetchers that provide data to be rendered client-side

* Provides endpoints to list valid fetchers exposed by plugins.
* Provides endpoints to run these fetchers.
"""

from flask_cors import CORS

from clue.api import bad_gateway, bad_request, make_subapi_blueprint, not_found, ok
from clue.common.exceptions import ClueException, NotFoundException
from clue.common.logging import get_logger
from clue.common.swagger import generate_swagger_docs
from clue.config import config
from clue.models.fetchers import FetcherDefinition
from clue.security import api_login
from clue.services import fetcher_service

logger = get_logger(__file__)


SUB_API = "fetchers"
fetchers_api = make_subapi_blueprint(SUB_API, api_version=1)
fetchers_api._doc = "Run fetchers for a given ID through configured external data sources/systems."

CORS(fetchers_api, origins=config.ui.cors_origins, supports_credentials=True)


@generate_swagger_docs(responses={200: "A list of types and their classification"})
@fetchers_api.route("/", methods=["GET"])
@api_login()
def get_fetchers(**kwargs) -> dict[str, FetcherDefinition]:
    """Return the supported fetchers of each external service.

    Variables:
    None

    Arguments:
    None

    Result Example:
    { # A dictionary of sources with their supported fetchers.
        <source_id>.<fetcher_id>: {
            "id": "<fetcher_id>",
            "classification": "",
            "description": "",
            "format": ""
            "supported_types": ["ip", ...]
        },
        ...,
    }
    """
    return ok(fetcher_service.get_plugins_supported_fetchers(kwargs["user"]))


@generate_swagger_docs(responses={200: "Successful lookup to selected plugins"})
@fetchers_api.route("/<plugin_id>/<fetcher_id>", methods=["POST"])
@api_login()
def run_fetcher(plugin_id: str, fetcher_id: str, **kwargs):
    """Search other services for additional information related to the provided data.

    Variables:
    plugin_id (str): the ID of the plugin who owns the action to execute
    fetcher_id (str): the ID of the action to execute

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
        return ok(fetcher_service.run_fetcher(plugin_id, fetcher_id, kwargs["user"]))
    except NotFoundException as err:
        return not_found(err=err.message)
    except ClueException as err:
        if err.status_code == 400:
            logger.warning("Bad request from fetcher %s.%s: %s", plugin_id, fetcher_id, err.message)
            return bad_request(err=err.message)

        logger.warning("Unknown error from fetcher %s.%s: %s", plugin_id, fetcher_id, err.message)
        return bad_gateway(err=err.message)
