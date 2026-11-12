"""Strict OpenID Connect client used for browser login and token refresh.

Authlib's default ID-token validation only constrains the issuer when provider metadata contains ``issuer``, only
checks the audience through ``azp``, and disables nonce validation when a token carries ``nonce_supported=false``.
This module replaces that validation with an explicit, non-overridable policy.
"""

import time
from threading import Lock
from typing import Any, Callable, Mapping

import requests
from authlib.integrations.flask_client import FlaskOAuth2App, OAuth
from authlib.jose import JsonWebKey, JsonWebToken
from authlib.oidc.core import CodeIDToken, UserInfo

from clue.common.exceptions import AuthenticationException
from clue.common.logging import get_logger
from clue.config import config
from clue.models.config import OAuthProvider
from clue.security.utils import PROVIDER_TOKEN_SIGNING_ALGORITHMS

logger = get_logger(__file__)

# Fields of the Clue provider configuration that are not Authlib client settings.
CLUE_ONLY_PROVIDER_FIELDS = (
    "auto_create",
    "auto_sync",
    "user_get",
    "auto_properties",
    "uid_regex",
    "uid_format",
    "user_groups",
    "user_groups_data_field",
    "user_groups_name_field",
    "app_provider",
)

ID_TOKEN_SIGNING_ALGORITHMS = PROVIDER_TOKEN_SIGNING_ALGORITHMS

DEFAULT_LEEWAY_SECONDS = 120

# Timeout for every request to the provider (token endpoint and JWKS), so a slow provider cannot hang a worker.
PROVIDER_HTTP_TIMEOUT_SECONDS = 10
# Cached signing keys are refreshed once older than this, so keys the provider withdrew stop being trusted.
JWKS_REFRESH_AFTER_SECONDS = 3600  # 1h
# Keys are never trusted longer than this after their last successful fetch, even if the provider is unreachable.
JWKS_MAX_AGE_SECONDS = 43200  # 12h


def _is_valid_jwk(jwk: Any) -> bool:
    """Whether an untrusted JWKS entry is a key object Authlib can import."""
    if not isinstance(jwk, dict):
        return False
    try:
        JsonWebKey.import_key(jwk)
    except Exception:  # Key material is untrusted; any parsing failure means the key is unusable.
        return False
    return True


class ClueOAuth2App(FlaskOAuth2App):
    """Flask OAuth2 client that enforces Clue's ID-token validation policy."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._jwks_lock = Lock()
        self._jwks_fetched_at: float | None = None
        self._jwks_attempted_at: float | None = None
        self._jwks_refresh_failed = False

    def _jwks_age(self, now: float) -> float | None:
        """Age of the cached JWKS, or None if there is none. Keys supplied at registration count from first use."""
        if not self.server_metadata.get("jwks"):
            return None
        if self._jwks_fetched_at is None:
            self._jwks_fetched_at = now
        return now - self._jwks_fetched_at

    def _usable_jwk_set(self, *, upstream_unavailable: bool = False) -> dict[str, Any]:
        """The cached JWKS if it is still within its maximum age; never stale keys."""
        age = self._jwks_age(time.monotonic())
        if age is None or age >= JWKS_MAX_AGE_SECONDS:
            if upstream_unavailable:
                raise requests.RequestException("The OAuth provider's signing keys are unavailable.")
            raise AuthenticationException("The ID token signing keys are unavailable.")
        return self.server_metadata["jwks"]

    def _download_jwk_set(self, uri: str) -> dict[str, Any]:
        with self.client_cls(**self.client_kwargs) as session:
            response = session.request("GET", uri, withhold_token=True, timeout=PROVIDER_HTTP_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload = response.json()

        if not isinstance(payload, dict) or not isinstance(payload.get("keys"), list):
            raise ValueError("Malformed JWKS payload")  # noqa: TRY004

        valid_keys = [jwk for jwk in payload["keys"] if _is_valid_jwk(jwk)]
        if payload["keys"] and not valid_keys:
            raise ValueError("JWKS contains no valid keys")
        return {"keys": valid_keys}

    def fetch_jwk_set(self, force: bool = False) -> dict[str, Any]:
        """Return the provider's signing keys, refreshing them when stale or when ``force`` is set.

        Unlike Authlib's default, cached keys expire, outbound fetches have a timeout, are serialized and rate-limited
        by ``jwks_refresh_cooldown_seconds`` (an unknown ``kid`` cannot trigger a request per login). A failed refresh
        may use still-valid cached keys; if none remain, the upstream failure is returned for retry. Keys older than
        ``JWKS_MAX_AGE_SECONDS`` are never used.
        """
        metadata = self.load_server_metadata()
        age = self._jwks_age(time.monotonic())
        if not force and age is not None and age < JWKS_REFRESH_AFTER_SECONDS:
            return metadata["jwks"]

        # Nonblocking: concurrent logins use the known keys instead of queueing behind a slow provider.
        if not self._jwks_lock.acquire(blocking=False):
            return self._usable_jwk_set(upstream_unavailable=True)

        try:
            now = time.monotonic()
            if (
                self._jwks_attempted_at is not None
                and now - self._jwks_attempted_at < config.auth.oauth.jwks_refresh_cooldown_seconds
            ):
                return self._usable_jwk_set(upstream_unavailable=self._jwks_refresh_failed)

            # Recorded before fetching so failed and timed-out attempts are rate-limited too.
            self._jwks_attempted_at = now
            uri = metadata.get("jwks_uri")
            if not uri:
                logger.critical("OAuth provider %s has no jwks_uri configured; refusing ID tokens", self.name)
                raise AuthenticationException("The ID token signing keys are unavailable.")

            try:
                jwk_set = self._download_jwk_set(uri)
            except (requests.RequestException, ValueError) as e:
                self._jwks_refresh_failed = True
                logger.warning("Failed to fetch the JWKS of OAuth provider %s [%s]", self.name, type(e).__name__)
                return self._usable_jwk_set(upstream_unavailable=True)

            metadata["jwks"] = jwk_set
            self._jwks_fetched_at = time.monotonic()
            self._jwks_refresh_failed = False
            return jwk_set
        finally:
            self._jwks_lock.release()

    def create_load_key(self) -> Callable[[dict[str, Any], Any], Any]:
        """Build a key loader that turns key lookup failures into authentication errors."""

        def find_key(jwk_set: Mapping[str, Any], header: Mapping[str, Any]) -> Any:
            return JsonWebKey.import_key_set(jwk_set).find_by_kid(header.get("kid"), use="sig", alg=header.get("alg"))

        def load_key(header: dict[str, Any], _payload: Any) -> Any:
            try:
                return find_key(self.fetch_jwk_set(), header)
            except ValueError:
                pass

            # The provider may have rotated its keys since they were cached.
            try:
                return find_key(self.fetch_jwk_set(force=True), header)
            except ValueError as e:
                raise AuthenticationException("The ID token signing key is not trusted.") from e

        return load_key

    def _trusted_issuer(self) -> str:
        issuer = self.load_server_metadata().get("issuer")
        if not issuer or not isinstance(issuer, str):
            logger.critical("OAuth provider %s has no trusted issuer configured (iss); refusing ID tokens", self.name)
            raise AuthenticationException("The OAuth provider has no trusted issuer configured.")
        return issuer

    def validate_callback_issuer(self, issuer: str | None) -> None:
        """Check the RFC 9207 ``iss`` authorization-response parameter against the trusted issuer.

        Rejects the callback before any code exchange when the parameter names another authorization server. Without
        a configured issuer there is nothing to compare with, so the parameter is ignored, as RFC 9207 permits.
        """
        if issuer is None:
            return

        trusted = self.load_server_metadata().get("issuer")
        if trusted and issuer != trusted:
            raise AuthenticationException("The OAuth callback was issued by an untrusted authorization server.")

    def _signing_algorithms(self) -> list[str]:
        advertised = self.load_server_metadata().get("id_token_signing_alg_values_supported")
        if not advertised:
            return list(ID_TOKEN_SIGNING_ALGORITHMS)

        algorithms = [alg for alg in ID_TOKEN_SIGNING_ALGORITHMS if alg in advertised]
        if not algorithms:
            raise AuthenticationException("The OAuth provider advertises no supported signing algorithm.")
        return algorithms

    def _validate_id_token(
        self, token: Mapping[str, Any], nonce: str | None, require_nonce: bool, leeway: int
    ) -> UserInfo:
        if not self.client_id:
            raise AuthenticationException("The OAuth provider has no client ID configured.")

        if require_nonce and (not nonce or not isinstance(nonce, str)):
            raise AuthenticationException("The authorization transaction has no nonce.")

        claims_options: dict[str, dict[str, Any]] = {
            "iss": {"essential": True, "value": self._trusted_issuer()},
            # Must contain the client ID; azp alone can never satisfy the audience requirement.
            "aud": {"essential": True, "values": [self.client_id]},
            "sub": {"essential": True},
            "exp": {"essential": True},
            "iat": {"essential": True},
        }
        claims_params: dict[str, Any] = {"client_id": self.client_id, "nonce": nonce if require_nonce else None}
        if require_nonce:
            claims_options["nonce"] = {"essential": True}
        if token.get("access_token"):
            claims_params["access_token"] = token["access_token"]

        claims = JsonWebToken(self._signing_algorithms()).decode(
            token["id_token"],
            key=self.create_load_key(),
            claims_cls=CodeIDToken,
            claims_options=claims_options,
            claims_params=claims_params,
        )
        # Unlike Authlib's default, a signed "nonce_supported" claim never disables nonce validation.
        claims.validate(leeway=leeway)
        return UserInfo(claims)

    def parse_id_token(
        self,
        token: Mapping[str, Any],
        nonce: str | None,
        claims_options: Any = None,  # noqa: ARG002
        claims_cls: Any = None,  # noqa: ARG002
        leeway: int = DEFAULT_LEEWAY_SECONDS,
    ) -> UserInfo | None:
        """Validate an ID token from a browser authorization-code callback.

        The nonce bound to the authorization transaction is mandatory. Caller-supplied claim options and classes are
        ignored so the policy cannot be weakened.
        """
        if "id_token" not in token:
            return None
        return self._validate_id_token(token, nonce=nonce, require_nonce=True, leeway=leeway)

    def parse_refreshed_id_token(self, token: Mapping[str, Any], leeway: int = DEFAULT_LEEWAY_SECONDS) -> UserInfo:
        """Validate an ID token returned by a refresh-token grant.

        A refresh grant has no authorization request and therefore no nonce, so the nonce is not compared. Signature,
        issuer, audience and temporal claims are enforced as for browser login.
        """
        return self._validate_id_token(token, nonce=None, require_nonce=False, leeway=leeway)


class ClueOAuth(OAuth):
    """Authlib Flask registry whose OAuth2 clients use :class:`ClueOAuth2App`."""

    oauth2_client_cls = ClueOAuth2App


def provider_client_kwargs(name: str, provider: OAuthProvider) -> dict[str, Any]:
    """Translate a Clue provider configuration into Authlib client registration arguments."""
    raw_provider: dict[str, Any] = provider.model_dump(mode="json", exclude_none=True)
    for field in CLUE_ONLY_PROVIDER_FIELDS:
        raw_provider.pop(field, None)

    # Authlib reads the trusted issuer from the "issuer" metadata key.
    issuer = raw_provider.pop("iss", None)
    if issuer:
        raw_provider["issuer"] = issuer

    # PKCE (RFC 7636) binds the authorization code to this transaction's session-stored verifier, for every provider.
    # default_timeout bounds the token-endpoint requests Authlib makes for login and refresh.
    raw_provider["client_kwargs"] = {
        "code_challenge_method": "S256",
        "default_timeout": PROVIDER_HTTP_TIMEOUT_SECONDS,
    }

    raw_provider["name"] = name
    return raw_provider


def build_oauth(providers: Mapping[str, OAuthProvider]) -> ClueOAuth:
    """Register every configured provider on a strict OAuth registry."""
    oauth = ClueOAuth()
    for name, provider in providers.items():
        oauth.register(**provider_client_kwargs(name, provider))
    return oauth
