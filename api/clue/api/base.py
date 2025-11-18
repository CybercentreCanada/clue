from flask import Blueprint, current_app, request

from clue.api import ok
from clue.common.logging import get_logger
from clue.security import api_login

logger = get_logger(__file__)

API_PREFIX = "/api"
api = Blueprint("api", __name__, url_prefix=API_PREFIX)

XSRF_ENABLED = True


#####################################
# API list API (API inception)
@api.route("/")
@api_login(audit=False)
def api_version_list(**_):
    """List all available API versions.

    Variables:
    None

    Arguments:
    None

    Data Block:
    None

    Result example:
    ["v1", "v2", "v3"]         #List of API versions available
    """
    api_list = []
    for rule in current_app.url_map.iter_rules():
        if rule.rule.startswith("/api/"):
            version = rule.rule[5:].split("/", 1)[0]
            if version not in api_list and version != "":
                # noinspection PyBroadException
                try:
                    int(version[1:])
                except ValueError:
                    continue
                api_list.append(version)

    return ok(api_list)


@api.route("/site_map/")
@api_login(audit=False)
def site_map(**_):
    """Check if all pages have been protected by a login decorator

    Variables:
    None

    Arguments:
    unsafe_only                    => Only show unsafe pages

    Data Block:
    None

    Result example:
    [                                #List of pages dictionary containing...
     {"function": views.default,     #Function name
      "url": "/",                    #Url to page
      "protected": true,             #Is function login protected
      "methods": ["GET"]},           #Methods allowed to access the page
    ]
    """
    pages = []
    for rule in current_app.url_map.iter_rules():
        func = current_app.view_functions[rule.endpoint]
        methods = []
        if rule.methods:
            for item in rule.methods:
                if item != "OPTIONS" and item != "HEAD":
                    methods.append(item)
        protected = func.__dict__.get("protected", False)
        audit = func.__dict__.get("audit", False)
        if "/api/v1/" in rule.rule:
            prefix = "api.v1."
        else:
            prefix = ""

        if "unsafe_only" in request.args and protected:
            continue

        pages.append(
            {
                "function": f"{prefix}{rule.endpoint.replace('apiv1.', '')}",
                "url": rule.rule,
                "methods": methods,
                "protected": protected,
                "audit": audit,
            }
        )

    return ok(sorted(pages, key=lambda i: i["url"]))
