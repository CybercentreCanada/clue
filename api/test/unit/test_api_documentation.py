from unittest.mock import patch

import pytest
from flask import Flask

from clue.api.base import api
from clue.api.v1 import apiv1
from clue.api.v1.lookup import lookup_api as lookup_v1_api
from clue.api.v2 import apiv2
from clue.api.v2.lookup import lookup_api as lookup_v2_api
from clue.models.auth_user import AuthResult, AuthUser, Privilege


@pytest.fixture
def app():
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    for blueprint in (api, apiv1, apiv2, lookup_v1_api, lookup_v2_api):
        app.register_blueprint(blueprint)
    return app


@pytest.mark.parametrize("version", [1, 2])
def test_documentation_requires_authentication(app, version):
    response = app.test_client().get(f"/api/v{version}/")
    assert response.status_code == 401


@pytest.mark.parametrize("trailing_slash", ["/", ""])
def test_all_advertised_versions_have_scoped_documentation(app, trailing_slash):
    auth = AuthResult(user=AuthUser(uname="test", classification="TLP:CLEAR"), privileges={Privilege.READ})
    headers = {"Authorization": "Bearer test"}
    with patch("clue.security.auth_service.bearer_auth", return_value=auth):
        client = app.test_client()
        versions = client.get("/api/", headers=headers).json["api_response"]
        assert set(versions) == {"v1", "v2"}
        for version in versions:
            response = client.get(f"/api/{version}{trailing_slash}", headers=headers)
            assert response.status_code == 200
            documentation = response.json["api_response"]
            assert documentation["blueprints"]["documentation"]
            assert documentation["apis"]
            for endpoint in documentation["apis"]:
                assert endpoint["path"].startswith(f"/api/{version}/")
                assert endpoint["function"].startswith(f"api.{version}.")
                assert endpoint["protected"]
                assert endpoint["complete"]
            assert any(
                endpoint["path"] == f"/api/{version}/lookup/types_detection/" for endpoint in documentation["apis"]
            )
