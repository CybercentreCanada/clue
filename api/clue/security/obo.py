from datetime import datetime
from typing import Optional

from clue.common.exceptions import InvalidDataException
from clue.common.logging import get_logger
from clue.config import config, get_redis
from clue.extensions import get_extensions
from clue.remote.datatypes.set import ExpiringSet
from clue.security.utils import decode_jwt_payload

logger = get_logger(__file__)


def _get_obo_token_store(service: str, user: str) -> ExpiringSet:
    """Get an expiring redis set in which to add a token

    Args:
        user (str): The user the token corresponds to

    Returns:
        ExpiringSet: The set in which we'll store the token
    """
    return ExpiringSet(f"{service}_token_{user}", host=get_redis(), ttl=60 * 5)


def _get_token_raw(service: str, user: str) -> Optional[str]:
    token_store = _get_obo_token_store(service, user)

    if token_store.length() > 0:
        result = token_store.random(1)

        if len(result) > 0:
            return result[0]

        logger.warning("Token store reported at least one entry, but was empty on fetch.")

    return None


def try_validate_expiry(obo_access_token: str):
    """Validates the expiry of an OBO (On-Behalf-Of) access token.

    Attempts to decode the JWT payload of the provided token and checks the 'exp' (expiry) field.
    If the token has expired, logs a warning and returns None.
    If the token is not a JWT or the 'exp' field is missing, logs a warning and skips expiry validation.

    Args:
        obo_access_token (str): The OBO access token to validate.

    Returns:
        str or None: The original token if valid or expiry cannot be determined, otherwise None if expired.
    """
    try:
        expiry = datetime.fromtimestamp(decode_jwt_payload(obo_access_token)["exp"])

        if expiry < datetime.now():
            logger.warning("Cached token has expired")
            return None
    except IndexError:
        logger.warning("Token is not a JWT, skipping expiry validation")
    except KeyError:
        logger.warning("'exp' field is missing, skipping expiry validation")

    return obo_access_token


def get_obo_token(service: str, access_token: str, user: str, force_refresh: bool = False):  # noqa: C901
    """Gets an On-Behalf-Of token from either the Redis cache or from the provided authentication plugin.

    Args:
        service (str): The target application we want a token for.
        access_token (str): The access token we want to use for the exchange.
        user (str): The name of the user.
        force_refresh (bool, optional): Allows to skip the Redis cache and get a new token. Defaults to False.

    Raises:
        InvalidDataException: Raised whenever an invalid OBO target is provided.

    Returns:
        Optional[str]: The access token for the targeted application.
    """
    if service not in config.api.obo_targets:
        raise InvalidDataException("Not a valid OBO target")

    # For testing purposes, we special-case test-obo
    if service == "test-obo":
        return access_token

    try:
        obo_access_token: str | None = None

        if not force_refresh:
            obo_access_token = _get_token_raw(service, user)

        if obo_access_token is not None:
            obo_access_token = try_validate_expiry(obo_access_token)

        if obo_access_token is None:
            logger.info(f"Fetching OBO token for user {user} to service {service}")

            extension_get_obo_token = None
            for extension in get_extensions():
                if extension.modules.obo_module:
                    extension_get_obo_token = extension.modules.obo_module
                    break

            if extension_get_obo_token is None:
                logger.info("No OBO function provided, returning provided access token")
                return access_token

            obo_access_token = extension_get_obo_token(service, access_token, user)

            if obo_access_token:
                service_token_store = _get_obo_token_store(service, user)
                service_token_store.pop_all()
                service_token_store.add(obo_access_token)
            else:
                logger.error("OBO failed, no token received.")
        else:
            logger.debug("Using cached OBO token")

        return obo_access_token
    except Exception:
        logger.exception("Exception on OBO:")
        return None
