from clue.common.logging import get_logger
from clue.config import config

logger = get_logger(__file__)


def generate_headers(obo_access_token: str | None, access_token: str | None) -> dict[str, str]:
    """Generates the request headers.

    Args:
        access_token (str): The access token to include in the Authorization header.

    Returns:
        dict[str, str]: A dict of the request headers
    """
    _headers = {
        "accept": "application/json",
        "content-type": "application/json",
    }

    if obo_access_token or access_token:
        logger.debug("Appending authorization header")
        _headers["Authorization"] = f"Bearer {obo_access_token or access_token}"

    if config.auth.propagate_clue_key and access_token:
        logger.debug("Appending custom authorization header")
        _headers["X-Clue-Authorization"] = access_token

    return _headers
