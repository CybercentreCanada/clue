import functools
from typing import Callable, Optional

import elasticapm
import requests
from flask import request
from jwt import ExpiredSignatureError
from prometheus_client import Counter

import clue.services.auth_service as auth_service
from clue.api import bad_request, forbidden, internal_error, not_found, unauthorized
from clue.common.exceptions import (
    AccessDeniedException,
    AuthenticationException,
    ClueAttributeError,
    ClueNotImplementedError,
    ClueRuntimeError,
    InvalidDataException,
    NotFoundException,
)
from clue.common.forge import APP_NAME
from clue.common.logging import get_logger
from clue.common.logging.audit import audit
from clue.config import AUDIT, config

logger = get_logger(__file__)

SUCCESSFUL_ATTEMPTS = Counter(
    f"{APP_NAME.replace('-', '_')}_auth_success_total",
    "Successful Authentication Attempts",
)

FAILED_ATTEMPTS = Counter(
    f"{APP_NAME.replace('-', '_')}_auth_fail_total",
    "Failed Authentication Attempts",
    ["status"],
)

XSRF_ENABLED = True


####################################
# API Helper func and decorators
# noinspection PyPep8Naming
class api_login(object):  # noqa: N801
    """Adds authentication to an endpoint"""

    def __init__(
        self,  # noqa: ANN101
        # TODO: Fix type parsing and checks
        # required_type: Optional[list[str]] = None,
        username_key: str = "username",
        audit: bool = True,
        required_priv: Optional[list[str]] = None,
        required_method: Optional[list[str]] = None,
        check_xsrf_token: bool = XSRF_ENABLED,
    ):
        if required_priv is None:
            required_priv = ["R", "W"]

        # TODO: Fix type parsing and checks
        # if required_type is None:
        #     required_type = ["admin", "user"]

        required_method_set: set[str]
        if required_method is None:
            required_method_set = {"userpass", "apikey", "internal", "oauth"}
        else:
            required_method_set = set(required_method)

        if len(required_method_set - {"userpass", "apikey", "internal", "oauth"}) > 0:
            raise ClueAttributeError("required_method must be a subset of {userpass, apikey, internal, oauth}")

        # TODO: Fix type parsing and checks
        # self.required_type = required_type
        self.audit = audit and AUDIT
        self.required_priv = required_priv
        self.required_method = required_method_set
        self.username_key = username_key
        self.check_xsrf_token = check_xsrf_token

    def __call__(self, func: Callable) -> Callable:  # noqa: ANN101, C901
        """Wraps any function calls with authentication logic that uses either userpass, apikey, internal or oauth.

        Args:
            func (Callable): The function to wrap with auth.

        Raises:
            AuthenticationException: Raised whenever there's an actual problem with the provided authentication.
            InvalidDataException: Raised whenever data is incorrectly formatted.
            ClueRuntimeError: Raised whenever there is a connection error with the oauth provider
            AccessDeniedException: Raised whenever the authentication is valid but the authenticated identity doesn't
                have the required access

        Returns:
            _type_: _description_
        """

        @functools.wraps(func)
        def base(*args, **kwargs):  # noqa: C901
            try:
                # All authorization (except impersonation) must go through the Authorization header, in one of
                # four formats:
                # 1. Basic user/pass authentication
                #       Authorization: Basic username:password (but in base64)
                # 2. Basic user/apikey authentication
                #       Authorization: Basic username:keyname:keydata (but in base64)
                # 3. Bearer internal token authentication (obtained from the login endpoint)
                #       Authorization: Bearer username:token
                # 4. Bearer OAuth authentication (obtained from external authentication provider i.e. azure, keycloak)
                #       Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjMifQ (example)
                authorization = request.headers.get("Authorization", None)
                if not authorization:
                    raise AuthenticationException("No Authorization header present")
                elif " " not in authorization or len(authorization.split(" ")) > 2:
                    raise InvalidDataException("Incorrectly formatted Authorization header")

                logger.debug("Authenticating user for path %s", request.path)

                [auth_type, data] = authorization.split(" ")

                user = None
                if auth_type == "Basic" and len(self.required_method & {"userpass", "apikey"}) > 0:
                    # Authenticate case (1) and (2) above
                    user, priv = auth_service.basic_auth(
                        data,
                        skip_apikey="apikey" not in self.required_method,
                        skip_password="userpass" not in self.required_method,
                    )
                elif auth_type == "Bearer" and len(self.required_method & {"internal", "oauth"}) > 0:
                    # Authenticate case (3) and (4) above
                    try:
                        user, priv = auth_service.bearer_auth(
                            data,
                            skip_jwt="oauth" not in self.required_method,
                            skip_internal="internal" not in self.required_method,
                        )
                    except ExpiredSignatureError as e:
                        raise AuthenticationException("Token Expired") from e
                    except (requests.exceptions.ConnectionError, ConnectionError) as e:
                        logger.exception("Failed to connect to OAuth Provider:")
                        raise ClueRuntimeError("Failed to connect to OAuth Provider") from e
                else:
                    raise InvalidDataException("Not a valid authentication type for this endpoint.")

                if not user:
                    raise AuthenticationException("No authenticated user found")

                # Ensure that the provided api key allows access to this API
                if not priv or not set(self.required_priv) & set(priv):
                    raise AccessDeniedException("You do not have access to this API.")

                # Make sure the user has the correct type for this endpoint
                # TODO: Fix type parsing and checks
                # if not set(self.required_type) & set(user["type"]):
                #     logger.warning(
                #         f"{user['uname']} is missing one of the types: {', '.join(self.required_type)}. "
                #         "Cannot access {request.path}"
                #     )
                #     raise AccessDeniedException(
                #         f"{request.path} requires one of the following user types: {', '.join(self.required_type)}"
                #     )

                ip = request.headers.get("X-Forwarded-For", request.remote_addr)
                logger.info(f"Logged in as {user['uname']} from {ip}")

                # If auditing is enabled, write this successful access to the audit logs
                if self.audit:
                    audit(
                        args,
                        kwargs,
                        user,
                        func,
                    )
            except (InvalidDataException, ClueNotImplementedError) as e:
                FAILED_ATTEMPTS.labels("400").inc()
                return bad_request(err=e.message)
            except AuthenticationException as e:
                FAILED_ATTEMPTS.labels("401").inc()
                return unauthorized(err=e.message)
            except AccessDeniedException as e:
                FAILED_ATTEMPTS.labels("403").inc()
                return forbidden(err=e.message)
            except NotFoundException:
                FAILED_ATTEMPTS.labels("404").inc()
                return not_found()
            except ClueRuntimeError as e:
                FAILED_ATTEMPTS.labels("500").inc()
                return internal_error(err=e.message)

            if config.core.metrics.apm_server.server_url is not None:
                elasticapm.set_user_context(
                    username=user.get("name", None),
                    email=user.get("email", None),
                    user_id=user.get("uname", None),
                )

            # Save user data in kwargs for future reference in the wrapped method
            kwargs["user"] = user

            SUCCESSFUL_ATTEMPTS.inc()
            return func(*args, **kwargs)

        base.protected = True
        # TODO: Fix type parsing and checks
        # base.required_type = self.required_type
        base.audit = self.audit
        base.required_priv = self.required_priv
        base.required_method = self.required_method
        base.check_xsrf_token = self.check_xsrf_token
        return base
