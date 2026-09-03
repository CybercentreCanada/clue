from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from flask import Flask

import clue.api.v1.auth as auth_api
import clue.services.auth_service as auth_service
from clue.common.exceptions import AccessDeniedException, InvalidDataException
from clue.config import config


def test_login_rejects_oauth_response_without_access_token():
    app = Flask(__name__)
    provider = Mock(client_id="client", client_secret="secret")
    provider.authorize_access_token.return_value = {}
    oauth = Mock()
    oauth.create_client.return_value = provider
    app.extensions["authlib.integrations.flask_client"] = oauth
    oauth_config = SimpleNamespace(
        enabled=True,
        providers={"keycloak": SimpleNamespace(client_id="client", client_secret="secret")},
    )

    with (
        app.test_request_context("/api/v1/auth/login?provider=keycloak&code=code"),
        patch.object(config.auth, "oauth", oauth_config),
    ):
        response = auth_api.login()

    assert response.status_code == 401
    assert response.json["api_error_message"] == "The OAuth provider did not return an access token."


def test_validate_apikey_uses_constant_time_secret_comparison():
    app = Flask(__name__)
    auth_config = SimpleNamespace(allow_apikeys=True, apikeys={"test-key": "expected-secret"})

    with (
        app.test_request_context(
            headers={
                "X-USERID": "analyst",
                "X-CLASSIFICATION": "TLP:CLEAR",
            }
        ),
        patch.object(config, "auth", auth_config),
        patch("clue.services.auth_service.hmac.compare_digest", return_value=False) as compare_digest,
        pytest.raises(AccessDeniedException, match="Invalid API key"),
    ):
        auth_service.validate_apikey("test-key", "provided-secret")

    compare_digest.assert_called_once_with(b"expected-secret", b"provided-secret")


def test_basic_auth_rejects_credentials_without_separator():
    with pytest.raises(InvalidDataException, match="key_name:key_secret"):
        auth_service.basic_auth("malformed", is_base64=False)
