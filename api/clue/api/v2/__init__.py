from flask import Blueprint

from clue.api.documentation import get_api_documentation

API_PREFIX = "/api/v2"
apiv2 = Blueprint("apiv2", __name__, url_prefix=API_PREFIX)
apiv2._doc = "Api Documentation - Version 2"  # type: ignore[attr-defined]
apiv2.add_url_rule("/", view_func=get_api_documentation)
