from flask import Blueprint

from clue.api.documentation import get_api_documentation

API_PREFIX = "/api/v1"
apiv1 = Blueprint("apiv1", __name__, url_prefix=API_PREFIX)
apiv1._doc = "Api Documentation - Version 1"  # type: ignore[attr-defined]
apiv1.add_url_rule("/", view_func=get_api_documentation)
