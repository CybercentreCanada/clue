"""Version 2 type detection metadata for enrichment lookups."""

from flask_cors import CORS

from clue.api import make_subapi_blueprint, ok
from clue.common.swagger import generate_swagger_docs
from clue.config import config
from clue.constants.supported_types import SupportedType
from clue.security import api_login
from clue.services import type_service

lookup_api = make_subapi_blueprint("lookup", api_version=2, blueprint_name="lookup_v2")
lookup_api._doc = "Type detection metadata with case sensitivity and priority."

CORS(lookup_api, origins=config.ui.cors_origins, supports_credentials=True)


@generate_swagger_docs(responses={200: "Supported types and their detection metadata"})
@lookup_api.route("/types_detection/", methods=["GET"])
@api_login()
def get_types_detection(**kwargs) -> dict[str, SupportedType]:
    """Return detection metadata for types exposed by accessible plugins.

    Variables:
    None

    Arguments:
    None

    Result Example:
    {
        "ipv4": {"regex": "<ipv4 regex>", "case_sensitive": True, "priority": 10},
        "domain": {"regex": "<domain regex>", "case_sensitive": False},
        "ip": {"regex": None, "case_sensitive": False}
    }

    Higher priorities win. Omitted priorities default to zero; equal priorities
    use the registry insertion order preserved in this response. Null regexes
    indicate types that must be specified explicitly rather than auto-detected.
    """
    return ok(type_service.get_types_detection(kwargs["user"]), sort_keys=False)
