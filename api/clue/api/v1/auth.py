from typing import Any, Callable, Mapping, Optional
from urllib.parse import urlencode

import requests
from authlib.integrations.base_client import OAuthError
from authlib.jose.errors import JoseError
from authlib.oidc.core import UserInfo
from flask import current_app, request
from pydantic import ValidationError

import clue.services.user_service as user_service
from clue.api import (
    bad_gateway,
    bad_request,
    forbidden,
    internal_error,
    make_subapi_blueprint,
    ok,
    unauthorized,
)
from clue.common.exceptions import (
    AccessDeniedException,
    AuthenticationException,
    ClueException,
    ClueValueError,
    InvalidDataException,
)
from clue.common.logging import get_logger
from clue.common.str_utils import default_string_value
from clue.common.swagger import generate_swagger_docs
from clue.config import config
from clue.models.auth_user import Privilege, RefreshRequest
from clue.security.oidc import ClueOAuth2App
from clue.security.utils import generate_random_secret

SUB_API = "auth"
auth_api = make_subapi_blueprint(SUB_API, api_version=1)
auth_api._doc = "Allow user to authenticate to the web server"  # type: ignore

logger = get_logger(__file__)

OAUTH_PROVIDER_PARAMS = frozenset({"provider", "oauth_provider"})
# Parameters an authorization server may append to the redirect URI: RFC 6749 section 4.1.2 (code, state, error*),
# OIDC Session Management (session_state) and RFC 9207 (iss). Anything else, notably credentials such as
# refresh_token, id_token or access_token, is rejected before any token exchange.
OAUTH_CALLBACK_PARAMS = OAUTH_PROVIDER_PARAMS | frozenset(
    {"code", "state", "session_state", "iss", "error", "error_description", "error_uri"}
)
# Transitional: UIs released before CLUE-010 add their own nonce to the login link and to the callback. It is accepted
# (once) so a cached UI can still sign in, then discarded: it is never read, so it cannot reach Authlib, the session or
# ID-token validation, which only use the nonce Authlib generated and stored for this browser session.
LEGACY_IGNORED_LOGIN_PARAMS = frozenset({"nonce"})
# Transitional: the JSON body those UIs post to this endpoint to refresh their tokens.
LEGACY_REFRESH_PARAMS = frozenset({"provider", "oauth_provider", "refresh_token"})
LEGACY_REFRESH_ERROR = "Token refresh moved to POST /api/v1/auth/refresh. Reload Clue and sign in again."
# Presence of any of these makes the request an authorization callback rather than a login initiation.
OAUTH_CALLBACK_MARKERS = frozenset({"code", "state", "error"})
# Keys that must never reach the browser login endpoint through a POST either.
OAUTH_POST_REJECTED_PARAMS = OAUTH_CALLBACK_PARAMS | frozenset(
    {"refresh_token", "id_token", "access_token", "nonce", "grant_type"}
)


def _is_legacy_refresh(body: Any) -> bool:
    """Whether a POST is the JSON token refresh that UIs released before CLUE-010 send to the login endpoint."""
    return (
        request.is_json
        and not request.args
        and isinstance(body, Mapping)
        and "refresh_token" in body
        and set(body.keys()) <= LEGACY_REFRESH_PARAMS
    )


def _single_valued(args: Mapping[str, Any], allowed: frozenset[str]) -> None:
    """Reject query strings containing unexpected or repeated parameters."""
    if not set(args.keys()) <= allowed:
        raise InvalidDataException("The OAuth request contains unexpected parameters.")

    getlist = getattr(args, "getlist", None)
    if getlist and any(len(getlist(key)) != 1 for key in args.keys()):
        raise InvalidDataException("The OAuth request contains repeated parameters.")


def _provider_name_from_args(args: Mapping[str, Any]) -> Optional[str]:
    names = {args[key] for key in OAUTH_PROVIDER_PARAMS if key in args}
    if len(names) > 1:
        raise InvalidDataException("Conflicting OAuth provider parameters.")
    return next(iter(names), None)


def _get_oauth_client(oauth_provider: str) -> tuple[ClueOAuth2App, dict[str, str]]:
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

    # Without this step, the provider will try and send the client_id and/or secret *twice*, leading to an error.
    kwargs: dict[str, str] = {}
    if not provider.client_id:
        client_id = default_string_value(
            oauth_provider_config.client_id, env_name=f"{oauth_provider.upper()}_CLIENT_ID"
        )
        if not client_id:
            logger.critical("client id not set! Cannot complete oauth")
            raise ClueValueError(
                f"No client ID configured for OAuth provider '{oauth_provider}' "
                f"(set it in config or {oauth_provider.upper()}_CLIENT_ID)."
            )
        kwargs["client_id"] = client_id

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


def _oauth_redirect_uri(oauth_provider: str) -> str:
    if not config.api.frontend_url:
        raise ClueValueError("api.frontend_url not set! Cannot start OAuth")

    return f"{config.api.frontend_url.rstrip('/')}/login?{urlencode({'provider': oauth_provider})}"


def _requests_openid(provider: ClueOAuth2App) -> bool:
    scope = provider.client_kwargs.get("scope") or provider.server_metadata.get("scope") or ""
    return "openid" in (scope.split() if isinstance(scope, str) else scope)


def _authenticated_response(
    oauth_provider: str, token_data: Mapping[str, Any], identity_data: Mapping[str, Any]
) -> Any:
    access_token = token_data.get("access_token", None)
    if not access_token:
        raise AuthenticationException("The OAuth provider did not return an access token.")

    try:
        cur_user = user_service.parse_user_data(dict(identity_data), oauth_provider)
    except ValidationError as e:
        raise AuthenticationException("The OAuth provider returned invalid user information.") from e

    logger.info(f"Login successful. (U:{cur_user.uname} - IP:{_client_ip()})")

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


def _client_ip() -> Optional[str]:
    return request.headers.get("X-Forwarded-For", request.remote_addr)


def _handle_auth_errors(handler: Callable[[], Any]) -> Any:
    """Map expected authentication failures to controlled responses that never echo tokens or callback data."""
    try:
        return handler()
    except (OAuthError, JoseError) as err:
        # Only the error class and code are logged: descriptions can contain provider- or attacker-supplied text.
        logger.warning(
            "OAuth/OIDC validation failure. (IP:%s) [%s: %s]",
            _client_ip(),
            type(err).__name__,
            getattr(err, "error", None),
        )
        return unauthorized(err="Authentication failed.")
    except AuthenticationException as err:
        logger.warning(f"Authentication failure. (IP:{_client_ip()}) [{err}]")
        return unauthorized(err=str(err))
    except AccessDeniedException as err:
        logger.warning(f"Authorization failure. (IP:{_client_ip()}) [{err}]")
        return forbidden(err=err.message)
    except InvalidDataException as err:
        return bad_request(err=err.message or str(err))
    except requests.RequestException as err:
        logger.warning("OAuth provider request failed. (IP:%s) [%s]", _client_ip(), type(err).__name__)
        return bad_gateway(err="The OAuth provider could not be reached. Try again later.")
    except ClueException:
        logger.exception(f"Internal Authentication Error. (IP:{_client_ip()})")
        return internal_error(err="Unhandled exception occured while Authenticating. Contact your administrator.")


# noinspection PyBroadException,PyPropertyAccess
@generate_swagger_docs()
@auth_api.route("/login", methods=["GET", "POST"])
def login(**_) -> dict[str, Any]:
    """Authenticate a user through an OAuth provider (browser authorization-code flow).

    The initial request redirects the user to the selected OAuth provider. The callback exchanges the authorization
    code bound to this browser session's ``state``, validates the returned ID token against the session-bound nonce,
    trusted issuer and client ID, and returns the provider-issued access token as the application token.

    Only the parameters listed below are accepted. Requests containing any other parameter (for example
    ``refresh_token``, ``id_token`` or ``access_token``) or a repeated parameter are rejected with a 400 before any
    token exchange. Token refresh is handled by ``POST /api/v1/auth/refresh``; the JSON refresh request that UIs
    released before this change post here gets a 401 without any token exchange, so they clear their credentials.

    Args:
        provider: The OAuth provider to use for authentication.
        oauth_provider: Alternative name for ``provider``.
        nonce: Deprecated and ignored. Still sent by UIs released before this change; never used for validation.
        code: The authorization code returned by the OAuth provider (callback only).
        state: The state returned by the OAuth provider (callback only).
        session_state: Provider session state, accepted and ignored (callback only).
        iss: Authorization server issuer identifier (RFC 9207). When present it must equal the provider's configured
            trusted issuer, otherwise the callback is rejected before the code exchange (callback only).
        error: OAuth error returned by the provider (callback only).
        error_description: OAuth error description returned by the provider (callback only).
        error_uri: OAuth error URI returned by the provider (callback only).

    Returns:
        A Clue API response containing the access token, refresh token, user information, and granted privileges.
        An initial authentication request returns the provider's authorization redirect response.

    Example:
        A successful authentication returns a response containing the provider
        token, privileges, and normalized user details::

            {
                "app_token": "<OAuth access token>",
                "provider": "keycloak",
                "refresh_token": "<OAuth refresh token>",
                "privileges": ["R", "W"],
                "user": {
                    "uname": "user",
                    "name": "User Name",
                    "email": "user@example.com",
                    "classification": "UNCLASSIFIED",
                    "groups": ["clue_user"],
                    "roles": ["user"],
                    "avatar": "data:image/png;base64, ..."
                }
            }
    """

    def handle() -> Any:
        # deny any post to request handle
        if request.method != "GET":
            body = request.get_json(silent=True) if request.is_json else request.form
            if _is_legacy_refresh(body):
                # Nothing is exchanged. The 401 makes those UIs clear their stored credentials instead of keeping
                # unusable tokens; the user then signs in again, and reloading loads the current UI.
                raise AuthenticationException(LEGACY_REFRESH_ERROR)

            keys = set(request.args.keys()) | (set(body.keys()) if isinstance(body, Mapping) else set())
            if keys & OAUTH_POST_REJECTED_PARAMS:
                raise InvalidDataException(
                    "OAuth login must use GET; token refresh must use POST /api/v1/auth/refresh."
                )
            raise AuthenticationException("Not enough information to proceed with authentication")

        args = request.args
        oauth_provider = _provider_name_from_args(args)
        if not oauth_provider:
            raise AuthenticationException("Not enough information to proceed with authentication")

        is_callback = bool(OAUTH_CALLBACK_MARKERS & args.keys())
        allowed = OAUTH_CALLBACK_PARAMS if is_callback else OAUTH_PROVIDER_PARAMS
        _single_valued(args, allowed | LEGACY_IGNORED_LOGIN_PARAMS)
        if is_callback and ("state" not in args or not ({"code", "error"} & args.keys())):
            raise AuthenticationException("The OAuth callback is missing its state or authorization code.")

        provider, kwargs = _get_oauth_client(oauth_provider)

        if not is_callback:
            # Authlib generates the state and nonce and binds them to this browser session.
            return provider.authorize_redirect(redirect_uri=_oauth_redirect_uri(oauth_provider))

        # Authlib rejects missing, forged, foreign-session and replayed state before exchanging the code, then
        # validates the ID token with ClueOAuth2App.parse_id_token against the session-bound nonce.
        provider.validate_callback_issuer(args.get("iss"))
        token_data = provider.authorize_access_token(**kwargs)
        if "id_token" in token_data or _requests_openid(provider):
            # Authlib replaces raw JSON userinfo with UserInfo only after parse_id_token succeeds.
            identity_data = token_data.get("userinfo")
            if "id_token" not in token_data or not isinstance(identity_data, UserInfo):
                raise AuthenticationException("The OAuth provider did not return a verified identity token.")
        else:
            identity_data = token_data.get("userinfo", token_data)

        return _authenticated_response(oauth_provider, token_data, identity_data)

    return _handle_auth_errors(handle)


@generate_swagger_docs()
@auth_api.route("/refresh", methods=["POST"])
def refresh(**_) -> dict[str, Any]:
    """Exchange an OAuth refresh token for a new access token.

    The request must be a JSON body containing exactly ``provider`` and ``refresh_token``; query parameters and form
    bodies are rejected so the refresh grant can never be selected from a browser navigation or OAuth callback URL.
    A returned ID token is validated for signature, trusted issuer, client ID audience and expiry.

    Args:
        provider: The OAuth provider that issued the refresh token.
        refresh_token: The OAuth refresh token.

    Returns:
        The same response as a successful ``/api/v1/auth/login`` callback.

    Example:
        A successful refresh returns the login response body with the new provider tokens::

            {"app_token": "<OAuth access token>", "refresh_token": "<OAuth refresh token>", "provider": "keycloak", ...}
    """

    def handle() -> Any:
        if request.args:
            raise InvalidDataException("Token refresh does not accept query parameters.")

        if not request.is_json:
            raise InvalidDataException("Token refresh requires a JSON body.")

        try:
            body = RefreshRequest.model_validate(request.get_json(silent=True))
        except ValidationError as e:
            raise InvalidDataException("Invalid token refresh request.") from e

        provider, kwargs = _get_oauth_client(body.provider)

        token_data = provider.fetch_access_token(
            refresh_token=body.refresh_token,
            grant_type="refresh_token",
            **kwargs,
        )
        if "id_token" in token_data:
            identity_data = provider.parse_refreshed_id_token(token_data)
        elif _requests_openid(provider):
            raise AuthenticationException("The OAuth provider did not return a verified identity token.")
        else:
            identity_data = token_data.get("userinfo", token_data)

        return _authenticated_response(body.provider, token_data, identity_data)

    return _handle_auth_errors(handle)
