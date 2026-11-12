from typing import Any

import requests
from authlib.integrations.base_client import OAuthError
from authlib.jose.errors import JoseError
from authlib.oidc.core import UserInfo
from flask import request
from pydantic import ValidationError

from clue.api import (
    bad_gateway,
    bad_request,
    forbidden,
    internal_error,
    make_subapi_blueprint,
    unauthorized,
)
from clue.common.exceptions import (
    AccessDeniedException,
    AuthenticationException,
    ClueException,
    InvalidDataException,
)
from clue.common.logging import get_logger
from clue.common.swagger import generate_swagger_docs
from clue.constants.oauth import (
    LEGACY_IGNORED_LOGIN_PARAMS,
    OAUTH_CALLBACK_MARKERS,
    OAUTH_CALLBACK_PARAMS,
    OAUTH_PROVIDER_PARAMS,
)
from clue.helper.oauth_login import (
    authenticated_response,
    client_ip,
    ensure_single_valued,
    get_oauth_client,
    oauth_redirect_uri,
    provider_name_from_args,
    requests_openid,
)
from clue.models.auth_user import RefreshRequest

SUB_API = "auth"
auth_api = make_subapi_blueprint(SUB_API, api_version=1)
auth_api._doc = "Allow user to authenticate to the web server"  # type: ignore

logger = get_logger(__file__)


# noinspection PyBroadException,PyPropertyAccess
@generate_swagger_docs()
@auth_api.route("/login", methods=["GET"])
def login(**_) -> dict[str, Any]:  # noqa: C901
    """Authenticate a user through an OAuth provider (browser authorization-code flow).

    The initial request redirects the user to the selected OAuth provider. The callback exchanges the authorization
    code bound to this browser session's ``state``, validates the returned ID token against the session-bound nonce,
    trusted issuer and client ID, and returns the provider-issued access token as the application token.

    Only the parameters listed below are accepted. Requests containing any other parameter (for example
    ``refresh_token``, ``id_token`` or ``access_token``) or a repeated parameter are rejected with a 400 before any
    token exchange. Only GET is allowed; token refresh is handled by ``POST /api/v1/auth/refresh``.

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
    try:
        args = request.args
        oauth_provider = provider_name_from_args(args)
        if not oauth_provider:
            raise AuthenticationException("Not enough information to proceed with authentication")

        is_callback = bool(OAUTH_CALLBACK_MARKERS & args.keys())
        allowed = OAUTH_CALLBACK_PARAMS if is_callback else OAUTH_PROVIDER_PARAMS
        ensure_single_valued(args, allowed | LEGACY_IGNORED_LOGIN_PARAMS)
        if is_callback and ("state" not in args or not ({"code", "error"} & args.keys())):
            raise AuthenticationException("The OAuth callback is missing its state or authorization code.")

        provider, kwargs = get_oauth_client(oauth_provider)

        if not is_callback:
            # Authlib generates the state and nonce and binds them to this browser session.
            return provider.authorize_redirect(redirect_uri=oauth_redirect_uri(oauth_provider))

        # Authlib rejects missing, forged, foreign-session and replayed state before exchanging the code, then
        # validates the ID token with ClueOAuth2App.parse_id_token against the session-bound nonce.
        provider.validate_callback_issuer(args.get("iss"))
        token_data = provider.authorize_access_token(**kwargs)
        if "id_token" in token_data or requests_openid(provider):
            # Authlib replaces raw JSON userinfo with UserInfo only after parse_id_token succeeds.
            identity_data = token_data.get("userinfo")
            if "id_token" not in token_data or not isinstance(identity_data, UserInfo):
                raise AuthenticationException("The OAuth provider did not return a verified identity token.")
        else:
            identity_data = token_data.get("userinfo", token_data)

        return authenticated_response(oauth_provider, token_data, identity_data)
    except (OAuthError, JoseError) as err:
        # Only the error class and code are logged: descriptions can contain provider- or attacker-supplied text.
        logger.warning(
            "OAuth/OIDC validation failure. (IP:%s) [%s: %s]",
            client_ip(),
            type(err).__name__,
            getattr(err, "error", None),
        )
        return unauthorized(err="Authentication failed.")
    except AuthenticationException as err:
        logger.warning(f"Authentication failure. (IP:{client_ip()}) [{err}]")
        return unauthorized(err=str(err))
    except AccessDeniedException as err:
        logger.warning(f"Authorization failure. (IP:{client_ip()}) [{err}]")
        return forbidden(err=err.message)
    except InvalidDataException as err:
        return bad_request(err=err.message or str(err))
    except requests.RequestException as err:
        logger.warning("OAuth provider request failed. (IP:%s) [%s]", client_ip(), type(err).__name__)
        return bad_gateway(err="The OAuth provider could not be reached. Try again later.")
    except ClueException:
        logger.exception(f"Internal Authentication Error. (IP:{client_ip()})")
        return internal_error(err="Unhandled exception occured while Authenticating. Contact your administrator.")


@generate_swagger_docs()
@auth_api.route("/refresh", methods=["POST"])
def refresh(**_) -> dict[str, Any]:  # noqa: C901
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
    try:
        if request.args:
            raise InvalidDataException("Token refresh does not accept query parameters.")

        if not request.is_json:
            raise InvalidDataException("Token refresh requires a JSON body.")

        try:
            body = RefreshRequest.model_validate(request.get_json(silent=True))
        except ValidationError as e:
            raise InvalidDataException("Invalid token refresh request.") from e

        provider, kwargs = get_oauth_client(body.provider)

        token_data = provider.fetch_access_token(
            refresh_token=body.refresh_token,
            grant_type="refresh_token",
            **kwargs,
        )
        if "id_token" in token_data:
            identity_data = provider.parse_refreshed_id_token(token_data)
        elif requests_openid(provider):
            raise AuthenticationException("The OAuth provider did not return a verified identity token.")
        else:
            identity_data = token_data.get("userinfo", token_data)

        return authenticated_response(body.provider, token_data, identity_data)
    except (OAuthError, JoseError) as err:
        # Only the error class and code are logged: descriptions can contain provider- or attacker-supplied text.
        logger.warning(
            "OAuth/OIDC validation failure. (IP:%s) [%s: %s]",
            client_ip(),
            type(err).__name__,
            getattr(err, "error", None),
        )
        return unauthorized(err="Authentication failed.")
    except AuthenticationException as err:
        logger.warning(f"Authentication failure. (IP:{client_ip()}) [{err}]")
        return unauthorized(err=str(err))
    except AccessDeniedException as err:
        logger.warning(f"Authorization failure. (IP:{client_ip()}) [{err}]")
        return forbidden(err=err.message)
    except InvalidDataException as err:
        return bad_request(err=err.message or str(err))
    except requests.RequestException as err:
        logger.warning("OAuth provider request failed. (IP:%s) [%s]", client_ip(), type(err).__name__)
        return bad_gateway(err="The OAuth provider could not be reached. Try again later.")
    except ClueException:
        logger.exception(f"Internal Authentication Error. (IP:{client_ip()})")
        return internal_error(err="Unhandled exception occured while Authenticating. Contact your administrator.")
