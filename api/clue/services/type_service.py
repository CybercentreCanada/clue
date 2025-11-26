from typing import Any

import requests
from elasticapm.traces import capture_span
from flask import request
from requests import exceptions

from clue.common.logging import get_logger
from clue.config import CLASSIFICATION, DEBUG, cache, config
from clue.constants.env import DISABLE_CACHE
from clue.constants.supported_types import SUPPORTED_TYPES
from clue.helper.headers import generate_headers
from clue.models.config import ExternalSource
from clue.remote.datatypes.cache import RedisCache
from clue.services import auth_service

logger = get_logger(__file__)

# Either cache for one second in debug mode, or five minutes in production
CACHE_TIMEOUT: int = 1 if DEBUG else 5 * 60
CACHE = RedisCache(prefix="clue_types", ttl=CACHE_TIMEOUT)


def get_types_regular_expressions(user: dict[str, Any]):
    """Return the regular expression to detect the different types"""
    access_token = request.headers.get("Authorization", type=str)
    if access_token:
        access_token = access_token.split(" ")[1]

    all_types = all_supported_types(
        user,
        access_token=access_token,
    )

    type_detection = {}

    for source_types in all_types.values():
        for data_type, classification in source_types.items():
            # Validate if the user is allow to even see the source
            if user and not CLASSIFICATION.is_accessible(user["classification"], classification):
                continue

            type_detection[data_type] = SUPPORTED_TYPES[data_type]

    return type_detection


@cache.memoize(timeout=CACHE_TIMEOUT)
def get_supported_types(source_url: str, access_token: str | None = None, obo_access_token: str | None = None):
    """Gets all supported types for the specified source.

    Args:
        source_url (str): The url of the source.
        access_token (str | None, optional): An access token giving access to the source. Defaults to None.

    Returns:
        Any: The supported types returned by the source.
    """
    url = f"{source_url}{'' if source_url.endswith('/') else '/'}types/"

    if not DISABLE_CACHE and (result := CACHE.get(url)):
        logger.info("Cache hit for url %s", url)
        return result

    logger.debug("Cache miss, polling plugin")
    with capture_span(f"GET {url}", span_type="http"):
        headers = generate_headers(obo_access_token or access_token, access_token if obo_access_token else None)

        try:
            rsp = requests.get(url, headers=headers, timeout=3.0)
        except (exceptions.ConnectionError, exceptions.ReadTimeout):
            # any errors are logged and no result is saved to local cache to enable retry on next query
            logger.exception(f"Unable to connect: {url}")
            return None

        status_code = rsp.status_code
        if status_code != 200:
            try:
                err = rsp.json()["api_error_message"]
                logger.error(f"Error ({rsp.status_code}) from upstream server: {status_code=}, {err=}")
                return None
            except requests.exceptions.JSONDecodeError:
                logger.exception(
                    f"Parsing error in error ({rsp.status_code}) response - unknown format\n"
                    f"Raw response: {rsp.text}"
                )
                return None
            except KeyError:
                logger.exception(
                    f"Parsing error in error ({rsp.status_code}) response - 'api_error_message' is missing\n",
                    f"Full response: {rsp.json()}",
                )
                return None
            except Exception:
                content = rsp.content
                if isinstance(content, (bytes, bytearray)):
                    content = content.decode()
                logger.exception(f"{source_url} encountered an unknown error.\n" f"Full response: {content}")
                return None

        try:
            types_result = rsp.json()["api_response"]
            logger.debug("Setting cache result for url %s", url)
            CACHE.set(url, types_result)
            return types_result
        except requests.exceptions.JSONDecodeError:
            logger.exception("Parsing error in OK response - unknown format\n" f"Raw response: {rsp.text}")
            return None
        except Exception:
            logger.exception("External API did not return expected format:")
            return None


def all_supported_types(user: dict[str, Any], access_token: str | None = None) -> dict[str, dict[str, str]]:
    """Gets supported types by all sources.

    Args:
        access_token (str | None, optional): An access token giving access to the sources. Defaults to None.

    Returns:
        dict[str, dict[str, str]]: A dict of each source and their supported types.
    """
    all_types = {}

    for source in config.api.external_sources:
        obo_access_token = None
        if access_token:
            obo_access_token, error = auth_service.check_obo(source, access_token, user["uname"])

            if error:
                logger.error("%s: %s", source.name, error)

        supported_types = get_supported_types(source.url, access_token=access_token, obo_access_token=obo_access_token)
        if supported_types is not None:
            all_types[source.name] = {k: v for k, v in supported_types.items() if k in SUPPORTED_TYPES}

    return all_types


def get_plugins_supported_types(user: dict[str, Any]):
    """Return the supported type names of each external service, filtered to what the user has access to."""
    configured_sources: list[ExternalSource] = getattr(config.api, "external_sources", [])
    available_types: dict[str, list[str]] = {}

    access_token = request.headers.get("Authorization", type=str)
    if access_token:
        access_token = access_token.split(" ")[1]

    all_types = all_supported_types(user, access_token=access_token)

    logger.info("Fetching sources for classification %s", user["classification"])

    for source in configured_sources:
        # Validate if the user is allow to even see the source
        if user and not CLASSIFICATION.is_accessible(user["classification"], source.classification):
            logger.info("Not including source %s at classification %s", source.name, user["classification"])
            continue

        # user can view source, now filter types user cannot see
        available_types[source.name] = [
            tname
            for tname, classification in all_types.get(source.name, {}).items()
            if user and CLASSIFICATION.is_accessible(user["classification"], classification)
        ]

    return available_types
