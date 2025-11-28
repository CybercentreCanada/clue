# implementation based on this stackoverflow post:
# https://stackoverflow.com/a/67943659


from typing import Any, Optional, cast

import jwt
import requests
from jwt.api_jwk import PyJWK

from clue.common.exceptions import ClueKeyError, ClueValueError
from clue.common.logging import get_logger
from clue.config import cache, config
from clue.security.utils import decode_jwt_payload

logger = get_logger(__file__)


def get_jwk(access_token: str) -> PyJWK:
    """Get the JSON Web Key associated with the given JWT"""
    # "kid" is the JSON Web Key's identifier. It tells us which key was used to validate the token.
    kid = jwt.get_unverified_header(access_token).get("kid")
    if not kid or not isinstance(kid, str):
        raise ClueValueError("Unexpected kid value in access token: %s", kid)

    jwks, _ = get_jwks()

    try:
        # Check to see if we have it cached
        key = PyJWK(jwks[kid])
    except KeyError:
        # We don't, so we need to refresh the key set
        cache.delete(key="get_jwks")
        try:
            jwks, _ = get_jwks()
            key = jwks[kid]
        except KeyError:
            raise ClueKeyError("There is no valid JWK for this token.")

    return key


def get_provider(access_token: str) -> str:
    """Get the provider of a given access token

    Args:
        access_token (str): The access token to determine the provider of

    Raises:
        ClueValueError: The provider of this access token does not match any supported providers

    Returns:
        str: The provider of the token
    """
    # "kid" is the JSON Web Key's identifier. It tells us which key was used to validate the token.
    kid = jwt.get_unverified_header(access_token).get("kid")
    if not kid or not isinstance(kid, str):
        raise ClueValueError("Unexpected kid value in access token: %s", kid)

    _, providers = get_jwks()

    try:
        # Check to see if we have it cached
        oauth_provider = providers[kid]
    except KeyError:
        # We don't, so we need to refresh the key set
        cache.delete(key="get_jwks")
        try:
            _, providers = get_jwks()
            oauth_provider = providers[kid]
        except KeyError:
            raise ClueValueError("The provider of this access token does not match any supported providers")

    return oauth_provider


@cache.cached(timeout=60 * 60 * 12, key_prefix="get_jwks")  # Cached for 12hrs
def get_jwks() -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Get the JSON Web Key Set for all supported providers

    Returns:
        tuple[dict[str, str], dict[str, str]]: The JWKS and the providers that are included in it
    """
    # JWKS = JSON Web Key Set. We merge the key set from all oauth providers
    jwks: dict[str, dict[str, Any]] = {}
    # Mapping of keys to their provider (i.e. azure, keycloak)
    providers: dict[str, str] = {}

    for (
        provider_name,
        provider_data,
    ) in config.auth.oauth.providers.items():
        # Fetch the JSON Web Key Set for each provider that supports them
        if provider_data.jwks_uri:
            provider_jwks = requests.get(provider_data.jwks_uri, timeout=10).json()["keys"]
            for jwk in provider_jwks:
                jwks[jwk["kid"]] = jwk
                providers[jwk["kid"]] = provider_name

    return (jwks, providers)


def extract_audience(access_token: str) -> list[str]:
    "Extract the audience from an encoded JWT."
    audience: list[str] | str | None = decode_jwt_payload(access_token).get("aud", None)

    if not audience:
        return []

    return [audience] if not isinstance(audience, list) else audience


def get_audience(oauth_provider: str) -> str:
    """Get the audience for the specified OAuth provider

    Args:
        oauth_provider (str): The OAuth provider to retrieve the audience of

    Raises:
        ClueValueError: The provider is azure, and is improperly formatted

    Returns:
        str: The audience of the provider
    """
    audience: str = "clue"
    provider_data = config.auth.oauth.providers[oauth_provider]
    if provider_data.audience:
        audience = provider_data.audience
    elif provider_data.client_id:
        audience = provider_data.client_id

    if oauth_provider == "azure" and f"{audience}/.default" not in provider_data.scope:
        raise ClueValueError("Azure scope must contain the <client_id>/.default claim!")

    return audience


def decode(
    access_token: str,
    key: Optional[str] = None,
    algorithms: Optional[list[str]] = None,
    audience: Optional[str] = None,
    validate_audience: bool = False,
    **kwargs,
) -> dict[str, Any]:
    """Decode an access token into a JSON Web Token dict

    Args:
        access_token (str): The access token to decode
        key (Optional[str], optional): The key used to sign the token. Defaults to None.
        algorithms (Optional[list[str]], optional): The algorithm to use when decoding. Defaults to None.
        audience (Optional[str], optional): The audience to check against, if validating the audience. Defaults to None.
        validate_audience (bool, optional): Should we validate the audience? Defaults to False.

    Returns:
        dict[str, Any]: The decoded JWT, in dict format
    """
    if not key:
        key = get_jwk(access_token).key

    if not algorithms:
        algorithms = [jwt.get_unverified_header(access_token).get("alg", "HS256")]

    if validate_audience and not audience:
        audience = get_audience(get_provider(access_token))

    try:
        return jwt.decode(
            jwt=access_token,
            key=cast(str, key),
            algorithms=algorithms,
            audience=audience,
            options={"verify_aud": validate_audience},
            **kwargs,
        )  # type: ignore
    except jwt.exceptions.InvalidAudienceError:
        logger.debug("Default audience did not match - checking additional audiences")
        if config.auth.oauth.other_audiences is not None:
            # The main audience isn't valid, let's try the others
            for audience in config.auth.oauth.other_audiences:
                logger.debug("Checking audience %s", audience)
                try:
                    return jwt.decode(
                        jwt=access_token,
                        key=cast(str, key),
                        algorithms=algorithms,
                        audience=audience,
                        options={"verify_aud": validate_audience},
                        **kwargs,
                    )  # type: ignore
                except jwt.InvalidAudienceError:
                    continue

        logger.warning(
            "Default and additional audiences failed to validate. Expected: %s, Actual: %s",
            audience,
            ",".join(extract_audience(access_token)),
        )
        raise


def fetch_sa_token() -> Optional[str]:
    """Use a service account to fetch a valid token, if service accounts are enabled"""
    if not config.auth.service_account.enabled:
        return None

    # TODO: Eventually support multiple accounts
    service_account = config.auth.service_account.accounts[0]
    cache_key = f"sa_refresh_token_{service_account.username}"

    provider = config.auth.oauth.providers[service_account.provider]

    try:
        # Eventually switch this to a redis cache (the rest of this file too)
        refresh_token = cache.get(key=cache_key)
        use_cache = True
    except AttributeError:
        refresh_token = None
        use_cache = False

    if refresh_token:
        sa_jwt = requests.post(
            provider.access_token_url,
            data={
                "client_id": provider.client_id,
                "client_secret": provider.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": provider.scope,
            },
            timeout=30,
        ).json()
    else:
        sa_jwt = requests.post(
            provider.access_token_url,
            data={
                "client_id": provider.client_id,
                "client_secret": provider.client_secret,
                "grant_type": "password",
                "username": service_account.username,
                "password": service_account.password,
                "scope": provider.scope,
            },
            timeout=30,
        ).json()

    if "error" in sa_jwt:
        logger.critical("[%s]: %s", sa_jwt["error"], sa_jwt["error_description"])
        return None

    if "refresh_token" in sa_jwt and use_cache:
        cache.set(cache_key, sa_jwt["refresh_token"], timeout=60 * 60 * 12)

    return sa_jwt["access_token"]
