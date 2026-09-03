from typing import Any, Optional
from urllib.parse import urlparse

from authlib.integrations.base_client import OAuthError
from flask import current_app, request
from pydantic import ValidationError

import clue.services.user_service as user_service
from clue.api import (
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
from clue.models.auth_user import Privilege
from clue.security.utils import generate_random_secret

logger = get_logger(__file__)


SUB_API = "auth"
auth_api = make_subapi_blueprint(SUB_API, api_version=1)
auth_api.__doc__ = "Allow user to authenticate to the web server"

logger = get_logger(__file__)


# noinspection PyBroadException,PyPropertyAccess
@generate_swagger_docs()
@auth_api.route("/login", methods=["GET", "POST"])
def login(**_) -> dict[str, Any]:  # noqa: C901
    """Authenticate a user through an OAuth provider.

    The initial request redirects the user to the selected OAuth provider.
    The callback exchanges the authorization code, validates the returned user,
    and returns the provider-issued access token as the application token.

    Args:
        provider: The OAuth provider to use for authentication.
        oauth_provider: Alternative name for ``provider``.
        code: The authorization code returned by the OAuth provider.
        refresh_token: An OAuth refresh token used to obtain a new access token.
        nonce: Optional nonce used during the OAuth authorization flow.

    Returns:
        A Clue API response containing the access token, refresh token, user
        information, and granted privileges. An initial authentication request
        returns the provider's authorization redirect response.

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

    Raises:
        AuthenticationException: If the OAuth provider does not return an access
            token or the authentication information is invalid.
        InvalidDataException: If OAuth is disabled.
    """
    data: dict[str, Any]
    if request.is_json and len(request.data) > 0:
        data = request.json  # type: ignore
    else:
        data = request.values

    # Get the ip the request came from - used in logging later
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    # Get the data from the request
    # TODO: Figure out how to fix this inconsistency
    oauth_provider = data.get("provider", data.get("oauth_provider", None))
    user = data.get("user", None)
    data.get("password", None)
    data.get("apikey", None)

    # These variables are what will eventually be returned, if authentication is successful
    logged_in_uname = None
    access_token = None
    refresh_token = data.get("refresh_token", None)
    priv: Optional[list[str]] = []

    try:
        # First, we'll try oauth
        if oauth_provider:
            if not config.auth.oauth.enabled:
                raise InvalidDataException("OAuth is disabled.")

            oauth = current_app.extensions.get("authlib.integrations.flask_client")
            if not oauth:
                logger.critical("Authlib integration missing!")
                raise ClueValueError()

            provider = oauth.create_client(oauth_provider)

            if not provider:
                logger.critical("OAuth client failed to create!")
                raise ClueValueError()

            # This means that they want to start the oauth process, so we'll redirect them to their chosen provider
            if "code" not in request.args and not refresh_token:
                referer = request.headers.get("Referer", None)
                uri = urlparse(referer if referer else request.host_url)
                port_portion = ":" + str(uri.port) if uri.port else ""
                redirect_uri = f"{uri.scheme}://{uri.hostname}{port_portion}/login?provider={oauth_provider}"
                return provider.authorize_redirect(redirect_uri=redirect_uri, nonce=request.args.get("nonce", None))

            # At this point we know the code exists, so we're good to use that to exchange for an JSON Web Token with
            # user data in it. token_data contains the access token, expiry, refresh token, and id token,
            # in JWT format: https://jwt.io/

            oauth_provider_config = config.auth.oauth.providers[oauth_provider]

            # We need to figure out what information the provider already has, and provide whatever it doesn't.
            # Without this step, the provider will try and send the client_id and/or secret *twice*, leading to an
            # error.
            kwargs = {}

            # Does the provider have the client id? If not provide it
            if not provider.client_id:
                kwargs["client_id"] = default_string_value(
                    oauth_provider_config.client_id,
                    env_name=f"{oauth_provider.upper()}_CLIENT_ID",
                )

                if not kwargs["client_id"]:
                    logger.critical("client id not set! Cannot complete oauth")
                    raise ClueValueError()

            # Does the provider have the client secret? If not provide it
            if not provider.client_secret:
                kwargs["client_secret"] = default_string_value(
                    oauth_provider_config.client_secret,
                    env_name=f"{oauth_provider.upper()}_CLIENT_SECRET",
                )

                if not kwargs["client_secret"]:
                    logger.critical("client secret not set! Cannot complete oauth")
                    raise ClueValueError()

            if refresh_token is not None:
                token_data = provider.fetch_access_token(
                    refresh_token=refresh_token,
                    grant_type="refresh_token",
                    **kwargs,
                )
            else:
                # Finally, ask for the access token with whatever info the provider needs
                token_data = provider.authorize_access_token(**kwargs)

            access_token = token_data.get("access_token", None)
            refresh_token = token_data.get("refresh_token", None)

            if not access_token:
                raise AuthenticationException("The OAuth provider did not return an access token.")

            # Get a useful dict of user data from the web token
            try:
                cur_user = user_service.parse_user_data(token_data, oauth_provider)
            except ValidationError as e:
                raise AuthenticationException("The OAuth provider returned invalid user information.") from e

            logged_in_uname = cur_user.uname

            priv = [Privilege.READ, Privilege.WRITE]

        # No oauth provider was specified, so we fall back to user/pass or user/apikey
        # elif user and (password or apikey):
        #     if password and apikey:
        #         raise InvalidDataException("Cannot specify password and API key.")

        #     user_data, priv = auth_service.basic_auth(
        #         f"{user}:{password or apikey}",
        #         is_base64=False,
        #         # No need to validate for api keys if we know they provided a password, and vice versa
        #         skip_apikey=bool(password),
        #         skip_password=bool(apikey),
        #     )

        #     if not user_data:
        #         raise AuthenticationException("User does not exist, or authentication was invalid")

        #     logged_in_uname = user_data["uname"]

        else:
            raise AuthenticationException("Not enough information to proceed with authentication")

    # For sanity's sake, we throw exceptions throughout the authentication code and simply catch the exceptions here to
    # return the corresponding HTTP Code to the user
    except (OAuthError, AuthenticationException) as err:
        logger.warning(f"Authentication failure. (U:{user} - IP:{ip}) [{err}]")
        return unauthorized(err=str(err))

    except AccessDeniedException as err:
        logger.warning(f"Authorization failure. (U:{user} - IP:{ip}) [{err}]")
        return forbidden(err=err.message)

    except InvalidDataException as err:
        return bad_request(err=err.message or str(err))

    except ClueException:
        logger.exception(f"Internal Authentication Error. (U:{user} - IP:{ip})")
        return internal_error(
            err="Unhandled exception occured while Authenticating. Contact your administrator.",
        )

    logger.info(f"Login successful. (U:{logged_in_uname} - IP:{ip})")

    xsrf_token = generate_random_secret()

    # Generate the token this user can use to authenticate from now on

    return ok(
        {
            "app_token": access_token,
            "provider": oauth_provider,
            "refresh_token": refresh_token,
            "privileges": priv,
            "user": cur_user.model_dump(mode="json"),
        },
        cookies={"XSRF-TOKEN": xsrf_token},
    )
