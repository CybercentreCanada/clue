# implementation based on this stackoverflow post:
# https://stackoverflow.com/a/67943659


import time
from collections.abc import Iterable
from threading import Lock
from typing import Any, Optional, cast

import jwt
import requests
from jwt.api_jwk import PyJWK

from clue.common.exceptions import ClueKeyError, ClueValueError
from clue.common.logging import get_logger
from clue.config import cache, config
from clue.models.jwks import JWKSSnapshot
from clue.security.utils import decode_jwt_payload

logger = get_logger(__file__)


# Shared across users in this worker so only one JWKS fetch can run at a time.
_jwks_refresh_lock = Lock()
_last_jwks_refresh_time: float | None = None
# Last successfully fetched JWKS. Kept outside SimpleCache so cache pressure can never lock out known keys.
_pinned_jwks: JWKSSnapshot | None = None
# Keys whose provider was last fetched longer ago than this are never served, from the cache or the pin.
MAX_PINNED_JWKS_STALE_SECONDS = 12 * 60 * 60
JWKS_CACHE_TIMEOUT_SECONDS = 60 * 60 * 12


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
        # The unverified kid may be attacker-controlled; refresh only if the cooldown permits it.
        try:
            jwks, _ = get_jwks(refresh=True)
            key = PyJWK(jwks[kid])
        except KeyError as e:
            raise ClueKeyError("There is no valid JWK for this token.") from e

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
        # Provider lookups use the same refresh cooldown as key lookups.
        try:
            _, providers = get_jwks(refresh=True)
            oauth_provider = providers[kid]
        except KeyError as e:
            raise ClueValueError("The provider of this access token does not match any supported providers") from e

    return oauth_provider


def _fresh_only(snapshot: JWKSSnapshot, now: float | None = None) -> JWKSSnapshot:
    """Filters out keys and providers whose last fetch is older than the stale TTL.

    This is pure: freshness is judged only by the timestamps carried in `snapshot`, never by module state,
    so a concurrent refresh cannot make an old snapshot look newer than it is.

    Args:
        snapshot: The snapshot of keys, kid owners and provider fetch times to filter.
        now: Reference monotonic time. Defaults to `time.monotonic()` when omitted.

    Returns:
        A new snapshot containing only providers fetched less than `MAX_PINNED_JWKS_STALE_SECONDS` before
        `now`, and the keys they own. Providers missing from `snapshot.timestamps` are treated as expired.
    """
    now = time.monotonic() if now is None else now
    fresh_providers = {
        name for name, fetched_at in snapshot.timestamps.items() if now - fetched_at < MAX_PINNED_JWKS_STALE_SECONDS
    }
    jwks = {kid: jwk for kid, jwk in snapshot.jwks.items() if snapshot.providers.get(kid) in fresh_providers}
    return JWKSSnapshot(
        jwks,
        {kid: snapshot.providers[kid] for kid in jwks},
        {name: fetched_at for name, fetched_at in snapshot.timestamps.items() if name in fresh_providers},
    )


def _unexpired_pinned_jwks() -> JWKSSnapshot | None:
    """Returns the pinned snapshot with expired providers removed, for use as a fallback.

    Returns:
        The unexpired part of the pinned snapshot, or None if there is no pinned snapshot or every provider has
        expired. A fresh provider that returned no keys is authoritative, so the result may have no keys.
    """
    pinned = _pinned_jwks  # single read: keys and timestamps travel together
    if pinned is None:
        return None

    fresh = _fresh_only(pinned)
    # Any fresh timestamp is authoritative, even with no keys; other providers' expired keys don't matter.
    return fresh if fresh.timestamps else None


def _known_jwks(cached_jwks: JWKSSnapshot | None) -> JWKSSnapshot:
    """Returns the best unexpired keys available without fetching.

    Used on cooldowns and while another request holds the refresh lock, so valid tokens keep verifying
    after cache evictions.

    Args:
        cached_jwks: The snapshot read from the cache, or None if it was evicted or never populated.

    Returns:
        The unexpired cached snapshot if there is one, otherwise the unexpired pinned snapshot, otherwise an
        empty snapshot.
    """
    if cached_jwks is not None:
        return _fresh_only(cached_jwks)
    return _unexpired_pinned_jwks() or JWKSSnapshot({}, {}, {})


def _is_valid_jwk(jwk: Any) -> bool:
    """Checks that an untrusted JWK entry is structurally usable.

    Args:
        jwk: A single entry from a provider's `keys` array.

    Returns:
        True if `jwk` is a dict with a non-empty string `kid`, a string `kty`, and key material that
        `PyJWK` accepts; False otherwise.
    """
    if not (
        isinstance(jwk, dict) and isinstance(jwk.get("kid"), str) and jwk["kid"] and isinstance(jwk.get("kty"), str)
    ):
        return False

    try:
        PyJWK(jwk)
    except Exception:  # Key material is untrusted; any parsing failure means the key is unusable.
        return False
    return True


def _fetch_provider_jwks(jwks_uri: str) -> list[dict[str, Any]]:
    """Fetches and validates one provider's JWKS.

    Args:
        jwks_uri: The provider's JWKS endpoint.

    Returns:
        The valid keys from the response. Malformed entries are skipped with a warning; an empty list is an
        authoritative "no keys" answer.

    Raises:
        requests.RequestException: The request failed or returned an HTTP error status.
        ValueError: The payload is not a JSON object with a `keys` list, or every entry in a non-empty
            `keys` list is malformed.
    """
    response = requests.get(jwks_uri, timeout=10)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("keys"), list):
        raise ValueError(f"Malformed JWKS payload from {jwks_uri}")  # noqa: TRY004

    valid_keys = [jwk for jwk in payload["keys"] if _is_valid_jwk(jwk)]
    skipped = len(payload["keys"]) - len(valid_keys)
    if skipped:
        logger.warning("Ignoring %d malformed JWK(s) from %s", skipped, jwks_uri)
    if payload["keys"] and not valid_keys:
        raise ValueError(f"JWKS from {jwks_uri} contains no valid keys")

    return valid_keys


def _fetch_all_providers(now: float) -> tuple[JWKSSnapshot, dict[str, Exception]]:
    """Fetches every configured provider independently so one failure cannot discard another's result.

    Args:
        now: Monotonic time recorded as the fetch time of each provider that succeeds.

    Returns:
        A snapshot of the providers that were fetched successfully (including those returning no keys), and
        the exception for each provider that failed.
    """
    jwks: dict[str, dict[str, Any]] = {}
    providers: dict[str, str] = {}
    timestamps: dict[str, float] = {}
    failures: dict[str, Exception] = {}
    for provider_name, provider_data in config.auth.oauth.providers.items():
        if not provider_data.jwks_uri:
            continue

        try:
            provider_jwks = _fetch_provider_jwks(provider_data.jwks_uri)
        except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError) as e:
            failures[provider_name] = e
            continue

        timestamps[provider_name] = now
        jwks |= {jwk["kid"]: jwk for jwk in provider_jwks}
        providers |= {jwk["kid"]: provider_name for jwk in provider_jwks}

    return JWKSSnapshot(jwks, providers, timestamps), failures


def _carry_over_failed_providers(fresh: JWKSSnapshot, failed: Iterable[str]) -> JWKSSnapshot:
    """Adds each failed provider's pinned keys, with their original fetch times, to a fresh snapshot.

    Expiry is not checked here: the caller runs `_fresh_only` on the result, so carried-over providers
    cannot outlive `MAX_PINNED_JWKS_STALE_SECONDS` however many partial refreshes happen.

    Args:
        fresh: Snapshot of the providers that were fetched successfully. Its entries win on a `kid` clash.
        failed: Names of providers whose refresh failed.

    Returns:
        A new snapshot combining `fresh` with the pinned data of the failed providers.
    """
    old = _pinned_jwks
    if old is None:
        return fresh

    carried = {kid for kid, owner in old.providers.items() if owner in failed}
    return JWKSSnapshot(
        {kid: old.jwks[kid] for kid in carried} | fresh.jwks,
        {kid: old.providers[kid] for kid in carried} | fresh.providers,
        {name: fetched_at for name, fetched_at in old.timestamps.items() if name in failed} | fresh.timestamps,
    )


def _get_jwks_snapshot(refresh: bool) -> JWKSSnapshot:
    global _last_jwks_refresh_time, _pinned_jwks

    cached_jwks: JWKSSnapshot | None = cache.get("get_jwks")
    if cached_jwks is not None and not refresh:
        return _fresh_only(cached_jwks)

    # Nonblocking: a waiting thread would stall behind a slow provider (up to the request timeout), so
    # overlapping callers serve existing keys or fail fast instead.
    if not _jwks_refresh_lock.acquire(blocking=False):
        return _known_jwks(cached_jwks)

    # The cache is only written inside this lock, and never with fallback data, so stale snapshots cannot roll it back.
    try:
        # Another request may have updated the cache before we acquired the lock.
        cached_jwks = cache.get("get_jwks")
        now = time.monotonic()
        if (
            _last_jwks_refresh_time is not None
            and now - _last_jwks_refresh_time < config.auth.oauth.jwks_refresh_cooldown_seconds
        ):
            return _known_jwks(cached_jwks)

        # Recorded before fetching so failed and timed-out attempts are rate-limited too; otherwise an attacker
        # sending unknown kids while a provider is down could trigger an outbound request per call.
        _last_jwks_refresh_time = now
        fetched, failures = _fetch_all_providers(now)

        if not fetched.timestamps:
            if not failures:
                return _known_jwks(cached_jwks)

            first_error = next(iter(failures.values()))
            fallback = _unexpired_pinned_jwks()
            if fallback is None:
                raise first_error
            logger.warning("Failed to refresh JWKS, serving pinned keys: %s", first_error)
            return fallback

        # Successful providers are authoritative (even with no keys); failed ones keep their unexpired pinned keys.
        if failures:
            logger.warning("Failed to refresh JWKS for providers %s", ", ".join(failures))

        # Re-checked with a fresh clock reading: slow requests may have pushed carried-over keys past the limit
        # since `now` was taken, and the caller must never receive a key that expired during the fetch.
        result = _fresh_only(_carry_over_failed_providers(fetched, failures), now=time.monotonic())
        # One assignment publishes keys and timestamps together, so readers never see mismatched generations.
        _pinned_jwks = result
        cache.set("get_jwks", result, timeout=JWKS_CACHE_TIMEOUT_SECONDS)
        return result
    finally:
        _jwks_refresh_lock.release()


def get_jwks(refresh: bool = False) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Get the JSON Web Key Set for all supported providers

    Args:
        refresh (bool): Request a refresh, subject to the outbound fetch cooldown.

    Returns:
        tuple[dict[str, str], dict[str, str]]: The JWKS and the providers that are included in it
    """
    snapshot = _get_jwks_snapshot(refresh)
    return snapshot.jwks, snapshot.providers


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
