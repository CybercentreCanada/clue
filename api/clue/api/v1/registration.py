from flask import request
from pydantic import ValidationError

from clue.api import bad_request, make_subapi_blueprint, no_content, ok
from clue.common.logging import get_logger
from clue.common.swagger import generate_swagger_docs
from clue.config import config, get_redis
from clue.models.config import ExternalSource
from clue.remote.datatypes.set import Set
from clue.security import api_login

logger = get_logger(__file__)

EXTERNAL_PLUGIN_SET = Set("plugin_set", host=get_redis())

SUB_API = "registration"
registration_api = make_subapi_blueprint(SUB_API, api_version=1)
registration_api._doc = "Register external plugins"


@generate_swagger_docs()
@registration_api.route("/register/", methods=["POST"])
@api_login()
def register_application(**kwargs):
    """Register the plugin given the provided data via REST API.

    Variables:
    None

    Arguments:
    None

    API Call Examples:
    /api/v1/registration/register/

    Data Block:
    [
        {
            "name": "test",
            "classification": "TLP:CLEAR",
            "max_classification": "TLP:CLEAR",
            "url": "http://localhost:5008/",
            "maintainer": "Example <example@example.com>",
            "datahub_link": "http://example.com",
            "documentation_link": "http://example.com"
        },
    ]

    Result Example:
    {
        "api_response": "test",         # The response from the API
        "api_error_message": "",         # Error message returned by the API
        "api_warning": [],               # List of warnings from the API
        "api_server_version": "1.0.0.dev0",  # Version of the API server
        "api_status_code": 200           # Status code returned by the API
    }

    """
    if not request.json:
        return bad_request(err="No data provided")

    try:
        registration_request = ExternalSource(**request.json, built_in=False)
    except ValidationError:
        return bad_request(err="Request data could not be converted to an ExternalSource object")

    config.api.external_sources.append(registration_request)
    EXTERNAL_PLUGIN_SET.add(registration_request.model_dump(mode="json", exclude_none=True))

    return ok(data=registration_request.name)


@generate_swagger_docs()
@registration_api.route("<plugin_id>", methods=["DELETE"])
@api_login()
def remove_application(plugin_id: str, **kwargs):
    """Remove the given plugin from the external_sources list via REST API.

    Variables:
    name  => "test"

    Optional Arguments:
    None

    API Call Examples:
    /api/v1/registration/test

    Result Example:
    {
        "response_status": "204 NO CONTENT"  # HTTP status code
    }
    """
    source_to_remove = None

    for source in config.api.external_sources:
        if source.name == plugin_id and source.built_in is False:
            source_to_remove = source
            break

    if (
        source_to_remove is not None
        and source_to_remove.model_dump(mode="json", exclude_none=True) in EXTERNAL_PLUGIN_SET.members()
    ):
        config.api.external_sources.remove(source_to_remove)
        EXTERNAL_PLUGIN_SET.remove(source_to_remove.model_dump(mode="json", exclude_none=True))
        logger.info(no_content(data=source_to_remove.name))
        return no_content(data=source_to_remove.name)

    return no_content(data=f"No plugin found with id: {plugin_id}")
