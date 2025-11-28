"""Enrichment Lookup

Lookup related data from external systems.

* Provide endpoints to list accepted types of data.
* Provide endpoints to query other systems to enable enrichment of such types.
"""

import json
import urllib.parse

from flask import request
from flask_cors import CORS
from pydantic import ValidationError

from clue.api import bad_request, make_subapi_blueprint, ok, unauthorized
from clue.common.exceptions import AuthenticationException, InvalidDataException
from clue.common.logging import get_logger
from clue.common.swagger import generate_swagger_docs
from clue.config import config
from clue.models.network import QueryResult
from clue.models.selector import Selector
from clue.security import api_login
from clue.services import lookup_service, type_service

logger = get_logger(__file__)


SUB_API = "lookup"
lookup_api = make_subapi_blueprint(SUB_API, api_version=1)
lookup_api._doc = "Lookup related data through configured external data sources/systems."

CORS(lookup_api, origins=config.ui.cors_origins, supports_credentials=True)


@generate_swagger_docs(responses={200: "A list of types and their classification"})
@lookup_api.route("/types/", methods=["GET"])
@api_login()
def get_types(**kwargs) -> dict[str, list[str]]:
    """Return the supported types of each external service.

    Variables:
    None

    Arguments:
    None

    Result Example:
    { # A dictionary of sources with their supported types.
        <source_name>: [
            <type name>,
            <type name>,
            ...,
        ],
        ...,
    }
    """
    return ok(type_service.get_plugins_supported_types(kwargs["user"]))


@generate_swagger_docs(responses={200: "A list of types and their regex detectors"})
@lookup_api.route("/types_detection/", methods=["GET"])
@api_login()
def get_types_detection(**kwargs) -> dict[str, str]:
    """Return the regular expression to detect the different types

    Variables:
    None

    Arguments:
    None

    Result Example:
    { # A dictionary of types with their associated regular expressions
        <type>: <regex>,
        ...
    }
    """
    return ok(type_service.get_types_regular_expressions(kwargs["user"]))


@generate_swagger_docs(responses={200: "Successful bulk lookup to selected plugins for included values"})
@lookup_api.route("/enrich", methods=["POST"])
@api_login()
def bulk_enrich(**kwargs) -> dict[str, dict[str, dict[str, QueryResult]]]:
    """Search other services for additional information related to the provided data.

    Variables:
    None

    Optional Arguments:
    classification: string  => Classification of the type [Default: minimum configured classification]
    sources: string         => | separated list of data sources. If empty, all configured sources are used.
    max_timeout: number     => Maximum execution time for the call in seconds
    limit: number           => limit the amount of returned results counted per source
    no_annotation: boolean  => Do not return any anotations
    no_cache: boolean       => Skip the cache and ask the plugins again
    include_raw: boolean    => Return raw plugin data
    exclude_unset: boolean  => Do not return any values that were not set by the plugin

    Data Block:
    [
        {"type": "ip", "value": "127.0.0.1"},
        ...
    ]

    Result Example:
    {                           # Dictionary of data source queried
        "ip": {
            "127.0.0.1":{
                "vt": {
                    "error": null,          # Error message returned by data source
                    "items": [              # list of results from the source
                        {
                            "link": "https://www.virustotal.com/gui/url/<id>",  # link to results
                            "count": 1,                                         # number of hits from the search
                            "classification": "TLP:C",                          # classification of the search result
                            "annotations": [                                    # Semi structured details about data
                                <Annotation data>
                            ],
                        },
                        ...,
                    ],
                },
                ...,
            },
            ...
        },
        ...
    }
    """
    user = kwargs["user"]

    post_data = request.json

    if not isinstance(post_data, list):
        return bad_request(err="Request data is not in the correct format")

    try:
        data = [Selector.model_validate(entry) for entry in post_data]
    except ValidationError as err:
        pydantic_errs: list[str] = []

        for validation_err in err.errors():
            loc = ".".join(
                section if isinstance(section, str) else f"[{str(section)}]" for section in validation_err["loc"]
            )
            pydantic_errs.append(f'"{loc}": {validation_err["msg"]}')

        return bad_request(err=f"Request data is not in the correct format: {', '.join(pydantic_errs)}")

    try:
        results = lookup_service.bulk_enrich(data, user)
    except AuthenticationException as e:
        return unauthorized(err=str(e))
    except InvalidDataException as e:
        return bad_request(err=str(e))

    return ok(results)


@generate_swagger_docs(responses={200: "Successful lookup to selected plugins"})
@lookup_api.route("/enrich/<type_name>/<value>/", methods=["GET"])
@api_login()
def enrich(type_name: str, value: str, **kwargs) -> dict[str, QueryResult]:
    """Search other services for additional information related to the provided data.

    Variables:
    type_name => Type of data to lookup in the external system.
    value => Value of the data to lookup. *Must be double URL encoded.*

    Optional Arguments:
    classification: string  => Classification of the type [Default: minimum configured classification]
    sources: string         => | separated list of data sources. If empty, all configured sources are used.
    max_timeout: number     => Maximum execution time for the call in seconds
    limit: number           => limit the amount of returned results counted per source
    no_annotation: boolean  => Do not return any anotations
    no_cache: boolean       => Skip the cache and ask the plugins again
    include_raw: boolean    => Return raw plugin data
    exclude_unset: boolean  => Do not return any values that were not set by the plugin

    API Call Examples:
    /api/v1/lookup/enrich/domain/malicious.domain/
    /api/v1/lookup/enrich/ip/1.1.1.1/?sources=vt|malware_bazar

    Result Example:
    {                           # Dictionary of data source queried
        "vt": {
            "error": null,          # Error message returned by data source
            "items": [              # list of results from the source
                {
                    "link": "https://www.virustotal.com/gui/url/<id>",   # link to results
                    "count": 1,                                          # number of hits from the search
                    "classification": "TLP:C",                           # classification of the search result
                    "annotations": [                                      # Semi structured details about type of data
                        <Annotation data>
                    ],
                },
                ...,
            ],
        },
        ...,
    }
    """
    user = kwargs["user"]

    # For backwards compatability, if eml is used it is replaced with email
    type_name = type_name.lower().replace("eml", "email")

    if type_name == "telemetry":
        try:
            json.loads(urllib.parse.unquote(value))
        except json.JSONDecodeError:
            return bad_request(err="If type is telemetry, value must be a valid JSON object.")
    else:
        # Normalize to lowercase all non-telemetry inputs
        value = value.lower()

    # re-encode the type after being decoded going through flask/wsgi route
    value = urllib.parse.quote(value, safe="")

    results = lookup_service.enrich(type_name, value, user)

    return ok(results)
