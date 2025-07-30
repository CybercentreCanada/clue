from http.client import HTTPException
from sys import exc_info
from traceback import format_tb
from typing import Union

from flask import Blueprint, request
from werkzeug.exceptions import BadRequest, Forbidden, InternalServerError, Unauthorized

from clue.api import bad_request, forbidden, internal_error, not_found, unauthorized
from clue.common.exceptions import (
    AccessDeniedException,
    AuthenticationException,
    ClueException,
)
from clue.common.logging import get_logger, log_with_traceback
from clue.common.logging.audit import AUDIT
from clue.config import config

errors = Blueprint("errors", __name__)

logger = get_logger(__file__)


######################################
# Custom Error page
@errors.app_errorhandler(400)
def handle_400(e: Union[HTTPException, ClueException]):
    """Handles HTTP 400 Bad Request errors.

    If the error is not an instance of BadRequest, the string representation of that error will be included in the
    response.

    Arguments:
        e: The error to handle.

    Returns:
        A Response object representing a Bad Request HTTP error.
    """
    if isinstance(e, BadRequest):
        error_message = "No data block provided or data block not in JSON format.'"
    else:
        error_message = str(e)
    return bad_request(err=error_message)


@errors.app_errorhandler(401)
def handle_401(e: Union[HTTPException, ClueException]):
    """Handles HTTP 401 Unauthorized errors.

    If the error is not an instance of Unauthorized, the string representation of that error will be included in the
    response. It will also clear the XSRF-TOKEN.

    Arguments:
        e: The error to handle.

    Returns:
        A Response object representing an Unauthorized HTTP error, also containing the oauth_providers data.
    """
    if isinstance(e, Unauthorized):
        msg = e.description
    else:
        msg = str(e)

    data = {"oauth_providers": [name for name in config.auth.oauth.providers.keys()]}
    res = unauthorized(data, err=msg)
    res.set_cookie("XSRF-TOKEN", "", max_age=0)
    return res


@errors.app_errorhandler(403)
def handle_403(e: Union[HTTPException, ClueException]):
    """Handles HTTP 403 Forbidden errors.

    If the error is not an instance of Forbidden, the string representation of that error will be included in the
    response. If the AUDIT config is enabled, this request will be logged.

    Arguments:
        e: The error to handle.

    Returns:
        A Response object representing a Forbidden HTTP error.
    """
    if isinstance(e, Forbidden):
        error_message = e.description
    else:
        error_message = str(e)

    trace = exc_info()[2]
    if AUDIT:
        uname = "(None)"
        ip = request.remote_addr

        log_with_traceback(trace, f"Access Denied. (U:{uname} - IP:{ip}) [{error_message}]", audit=True)

    return forbidden(err=f"Access Denied ({request.path}) [{error_message}]")


@errors.app_errorhandler(404)
def handle_404(_):
    """Handles HTTP 404 Not Found errors."""
    return not_found(err=f"Api does not exist ({request.path})")


@errors.app_errorhandler(500)
def handle_500(e: InternalServerError):
    """Handles HTTP 500 Internal Server errors.

    If the original_exception of e is an AccessDeniedException or AuthenticationException, this redirects to the 403 or
    401 error handlers, otherwise it logs it and returns a formatted error message.

    Arguments:
        e: The error to handle.

    Returns:
        A Response object representing an Internal Server HTTP error.
    """
    if isinstance(e.original_exception, AccessDeniedException):
        return handle_403(e.original_exception)

    if isinstance(e.original_exception, AuthenticationException):
        return handle_401(e.original_exception)

    oe = e.original_exception or e

    trace = exc_info()[2]
    log_with_traceback(trace, "Exception", is_exception=True)

    message = "".join(["\n"] + format_tb(exc_info()[2]) + ["%s: %s\n" % (oe.__class__.__name__, str(oe))]).rstrip("\n")
    return internal_error(err=message)
