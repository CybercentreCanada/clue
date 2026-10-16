"""Strict OpenID Connect client used for browser login and token refresh.

Authlib's default ID-token validation only constrains the issuer when provider metadata contains ``issuer``, only
checks the audience through ``azp``, and disables nonce validation when a token carries ``nonce_supported=false``.
This module replaces that validation with an explicit, non-overridable policy.
"""

from typing import Any, Callable, Mapping

from authlib.integrations.flask_client import FlaskOAuth2App, OAuth
from authlib.jose import JsonWebKey, JsonWebToken
from authlib.oidc.core import CodeIDToken, UserInfo

from clue.common.exceptions import AuthenticationException
from clue.common.logging import get_logger
from clue.common.str_utils import default_string_value
from clue.models.config import OAuthProvider

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

# Asymmetric algorithms only: symmetric or "none" algorithms must never verify a provider-issued ID token.
ID_TOKEN_SIGNING_ALGORITHMS = (
    "RS256",
    "RS384",
    "RS512",
    "PS256",
    "PS384",
    "PS512",
    "ES256",
    "ES384",
    "ES512",
    "EdDSA",
)

DEFAULT_LEEWAY_SECONDS = 120


class ClueOAuth2App(FlaskOAuth2App):
    """Flask OAuth2 client that enforces Clue's ID-token validation policy."""

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

    client_id = default_string_value(provider.client_id, env_name=f"{name.upper()}_CLIENT_ID")
    if client_id:
        raw_provider["client_id"] = client_id

    raw_provider["name"] = name
    return raw_provider


def build_oauth(providers: Mapping[str, OAuthProvider]) -> ClueOAuth:
    """Register every configured provider on a strict OAuth registry."""
    oauth = ClueOAuth()
    for name, provider in providers.items():
        oauth.register(**provider_client_kwargs(name, provider))
    return oauth
