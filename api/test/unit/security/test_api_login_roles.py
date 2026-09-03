from unittest.mock import patch

from flask import Flask

from clue.models.auth_user import AuthResult, AuthUser, Privilege, UserRole
from clue.security import api_login


def _AuthResult(*roles: UserRole) -> AuthResult:
    return AuthResult(
        user=AuthUser(
            uname="analyst",
            email="analyst@example.com",
            classification="TLP:CLEAR",
            roles=set(roles),
        ),
        privileges={Privilege.READ, Privilege.WRITE},
    )


def test_api_login_rejects_user_from_admin_endpoint():
    app = Flask(__name__)

    @api_login(required_roles=[UserRole.ADMIN], audit=False)
    def admin_endpoint(**kwargs):
        return kwargs["user"]

    with (
        app.test_request_context("/admin", headers={"Authorization": "Bearer token.value.signature"}),
        patch("clue.security.auth_service.bearer_auth", return_value=_AuthResult(UserRole.USER)),
    ):
        response = admin_endpoint()

    assert response.status_code == 403


def test_api_login_allows_admin_to_reach_endpoint():
    app = Flask(__name__)

    @api_login(required_roles=[UserRole.ADMIN], audit=False)
    def admin_endpoint(**kwargs):
        return kwargs["user"]

    with (
        app.test_request_context("/admin", headers={"Authorization": "Bearer token.value.signature"}),
        patch(
            "clue.security.auth_service.bearer_auth",
            return_value=_AuthResult(UserRole.USER, UserRole.ADMIN),
        ),
    ):
        user = admin_endpoint()

    assert UserRole.ADMIN in user["roles"]
