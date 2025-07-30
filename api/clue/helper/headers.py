from clue.common.logging import get_logger
from clue.config import DEBUG, cache, config

logger = get_logger(__file__)


@cache.memoize(timeout=1 if DEBUG else 5 * 60)  # Cached for 5 minutes
def generate_headers(access_token: str | None, clue_access_token: str | None) -> dict[str, str]:
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

    if access_token:
        logger.debug("Appending authorization header")
        _headers["Authorization"] = f"Bearer {access_token}"

    if config.auth.propagate_clue_key and clue_access_token:
        logger.debug("Appending custom authorization header")
        _headers["X-Clue-Authorization"] = clue_access_token

    return _headers
