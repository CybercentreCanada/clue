"""Request validation, client resolution and response helpers for the OAuth login and token refresh endpoints."""

from typing import Any, Mapping, Optional
from urllib.parse import urlencode

from flask import current_app, request
from pydantic import ValidationError

import clue.services.user_service as user_service
from clue.api import ok
from clue.common.exceptions import AuthenticationException, ClueValueError, InvalidDataException
from clue.common.logging import get_logger
from clue.common.str_utils import default_string_value
from clue.config import config
from clue.constants.oauth import OAUTH_PROVIDER_PARAMS
from clue.models.auth_user import Privilege
from clue.security.oidc import ClueOAuth2App
from clue.security.utils import generate_random_secret

logger = get_logger(__file__)


def ensure_single_valued(args: Mapping[str, Any], allowed: frozenset[str]) -> None:
    """Reject query strings containing unexpected or repeated parameters."""
    if not set(args.keys()) <= allowed:
        raise InvalidDataException("The OAuth request contains unexpected parameters.")

    getlist = getattr(args, "getlist", None)
    if getlist and any(len(getlist(key)) != 1 for key in args.keys()):
        raise InvalidDataException("The OAuth request contains repeated parameters.")


def provider_name_from_args(args: Mapping[str, Any]) -> Optional[str]:
    """The OAuth provider named by ``provider`` or ``oauth_provider``; both may be given only if they agree."""
    names = {args[key] for key in OAUTH_PROVIDER_PARAMS if key in args}
    if len(names) > 1:
        raise InvalidDataException("Conflicting OAuth provider parameters.")
    return next(iter(names), None)


def get_oauth_client(oauth_provider: str) -> tuple[ClueOAuth2App, dict[str, str]]:
    """Resolve a configured OAuth client and any client credentials Authlib does not already hold."""
    if not config.auth.oauth.enabled:
        raise InvalidDataException("OAuth is disabled.")

    if not isinstance(oauth_provider, str) or oauth_provider not in config.auth.oauth.providers:
        raise InvalidDataException("Unknown OAuth provider.")

    oauth = current_app.extensions.get("authlib.integrations.flask_client")
    if not oauth:
        logger.critical("Authlib integration missing!")
        raise ClueValueError("Authlib OAuth registry is not initialized on the Flask app.")

    provider = oauth.create_client(oauth_provider)
    if not provider:
        logger.critical("OAuth client failed to create!")
        raise ClueValueError(f"Authlib could not create an OAuth client for provider '{oauth_provider}'.")

    oauth_provider_config = config.auth.oauth.providers[oauth_provider]

    # The client ID is resolved from config or <PROVIDER>_CLIENT_ID when the configuration loads (OAuth.prepare_model).
    if not provider.client_id:
        logger.critical("client id not set! Cannot complete oauth")
        raise ClueValueError(
            f"No client ID configured for OAuth provider '{oauth_provider}' "
            f"(set it in config or {oauth_provider.upper()}_CLIENT_ID)."
        )

    # Without this step, the provider will try and send the client_secret *twice*, leading to an error.
    kwargs: dict[str, str] = {}
    if not provider.client_secret:
        client_secret = default_string_value(
            oauth_provider_config.client_secret, env_name=f"{oauth_provider.upper()}_CLIENT_SECRET"
        )
        if not client_secret:
            logger.critical("client secret not set! Cannot complete oauth")
            raise ClueValueError(
                f"No client secret configured for OAuth provider '{oauth_provider}' "
                f"(set it in config or {oauth_provider.upper()}_CLIENT_SECRET)."
            )
        kwargs["client_secret"] = client_secret

    return provider, kwargs


def oauth_redirect_uri(oauth_provider: str) -> str:
    """The frontend login URL the OAuth provider redirects back to."""
    if not config.api.frontend_url:
        raise ClueValueError("api.frontend_url not set! Cannot start OAuth")

    return f"{config.api.frontend_url.rstrip('/')}/login?{urlencode({'provider': oauth_provider})}"


def requests_openid(provider: ClueOAuth2App) -> bool:
    """Whether the provider is configured with the ``openid`` scope, so a verified ID token is required."""
    scope = provider.client_kwargs.get("scope") or provider.server_metadata.get("scope") or ""
    return "openid" in (scope.split() if isinstance(scope, str) else scope)


def client_ip() -> Optional[str]:
    """The client IP address, for logging."""
    return request.headers.get("X-Forwarded-For", request.remote_addr)


def authenticated_response(oauth_provider: str, token_data: Mapping[str, Any], identity_data: Mapping[str, Any]) -> Any:
    """Build the successful login/refresh response from the provider's tokens and the user's identity."""
    access_token = token_data.get("access_token", None)
    if not access_token:
        raise AuthenticationException("The OAuth provider did not return an access token.")

    try:
        cur_user = user_service.parse_user_data(dict(identity_data), oauth_provider)
    except ValidationError as e:
        raise AuthenticationException("The OAuth provider returned invalid user information.") from e

    logger.info(f"Login successful. (U:{cur_user.uname} - IP:{client_ip()})")

    return ok(
        {
            "app_token": access_token,
            "provider": oauth_provider,
            "refresh_token": token_data.get("refresh_token", None),
            "privileges": [Privilege.READ, Privilege.WRITE],
            "user": cur_user.model_dump(mode="json"),
        },
        cookies={"XSRF-TOKEN": generate_random_secret()},
    )
