from flasgger import swag_from
from flask import Blueprint, abort, make_response

from clue.config import get_redis

API_PREFIX = "/healthz"
healthz = Blueprint("healthz", __name__, url_prefix=API_PREFIX)


@swag_from(
    {
        "parameters": [],
        "definitions": {},
        "responses": {"200": {"description": "Liveness Probe"}},
        "tags": ["Health"],
        "operationId": "clue.healthz.liveness",
    }
)
@healthz.route("/live")
def liveness(**_):
    """Check if the API is live

    Variables:
    None

    Arguments:
    None

    Data Block:
    None

    Result example:
    OK or FAIL
    """
    return make_response("OK")


@swag_from(
    {
        "parameters": [],
        "definitions": {},
        "responses": {"200": {"description": "Readyness Probe"}},
        "tags": ["Health"],
        "operationId": "clue.healthz.readyness",
    }
)
@healthz.route("/ready")
def readyness(**_):
    """Check if the API is Ready

    Variables:
    None

    Arguments:
    None

    Data Block:
    None

    Result example:
    OK or FAIL
    """
    redis = get_redis()

    if redis.ping():
        return make_response("OK")
    else:
        abort(503)


@healthz.errorhandler(503)
def error(_):
    "Handle errors exposed in healthz routes"
    return "FAIL", 503
