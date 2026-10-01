from typing import Any, Optional

from flask import has_request_context, request

from clue.common.exceptions import AuthenticationException
from clue.common.logging import get_logger
from clue.models.config import ExternalSource
from clue.services import auth_service

logger = get_logger(__file__)


def get_obo_access_token(
    source: ExternalSource, user: dict[str, Any], access_token: Optional[str] = None
) -> tuple[Optional[str], Optional[str]]:
    """Get the caller access token and an OBO token for an external source when needed."""
    if access_token is None and has_request_context():
        auth_header = request.headers.get("Authorization", type=str)
        if auth_header:
            parts = auth_header.split(" ", 1)
            access_token = parts[1] if len(parts) == 2 else auth_header

    if not access_token:
        return None, None

    obo_access_token, error = auth_service.check_obo(source, access_token, user["uname"])
    if error:
        logger.error("%s: %s", source.name, error)
        raise AuthenticationException("Invalid token provided for this enrichment.")

    return access_token, obo_access_token
