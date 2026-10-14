import time
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest
from authlib.integrations.flask_client import OAuth
from authlib.jose import JsonWebKey, jwt
from flask import Flask
from pydantic import ValidationError

import clue.api.v1.auth as auth_api
import clue.services.auth_service as auth_service
import clue.services.user_service as user_service
from clue.common.exceptions import AccessDeniedException, InvalidDataException
from clue.config import config
from clue.models.auth_user import APIKeyConf, AuthUser, UserRole
from clue.models.config import ExternalSource, OAuthProvider

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


@pytest.fixture
def oidc(monkeypatch):
    """Real Authlib client and Flask session; only the token endpoint is mocked."""
    app = Flask("clue_010_oidc")
    app.config.update(TESTING=True, SECRET_KEY="local-test-only", SESSION_COOKIE_SECURE=True)
    app.register_blueprint(auth_api.auth_api)
    provider_config = OAuthProvider(
        client_id="local-client",
        client_secret="local-test-only",
        authorize_url="https://provider.invalid/authorize",
        access_token_url="https://provider.invalid/token",
        api_base_url=None,
        audience="local-client",
        scope="openid email profile",
        iss="https://provider.invalid",
        jwks_uri="https://provider.invalid/keys",
    )
    # Mirrors provider registration in clue/app.py
    raw_provider = provider_config.model_dump(mode="json", exclude_none=True)
    for field in CLUE_ONLY_PROVIDER_FIELDS:
        raw_provider.pop(field, None)
    oauth = OAuth()
    oauth.register(name="local", **raw_provider)
    oauth.init_app(app)
    provider = oauth.create_client("local")
    signing_key = JsonWebKey.generate_key("RSA", 2048, is_private=True)
    provider.server_metadata["jwks"] = {"keys": [signing_key.as_dict(is_private=False)]}
    monkeypatch.setattr(
        config.auth,
        "oauth",
        SimpleNamespace(enabled=True, gravatar_enabled=False, providers={"local": provider_config}),
    )
    monkeypatch.setattr("requests.sessions.Session.request", Mock(side_effect=AssertionError("Network forbidden")))
    exchange = Mock()
    monkeypatch.setattr(provider, "fetch_access_token", exchange)

    def token(nonce=None, key=None):
        claims = {
            "iss": "https://provider.invalid",
            "sub": "local-user",
            "aud": "local-client",
            "exp": int(time.time()) + 300,
            "iat": int(time.time()),
            "preferred_username": "local-user",
        }
        if nonce is not None:
            claims["nonce"] = nonce
        return {
            "access_token": "synthetic-access",
            "refresh_token": "synthetic-refresh",
            "id_token": jwt.encode({"alg": "RS256"}, claims, key or signing_key).decode(),
        }

    return SimpleNamespace(app=app, client=app.test_client(), exchange=exchange, token=token)


def begin_login(oidc, client=None, query="provider=local"):
    response = (client or oidc.client).get(f"/api/v1/auth/login?{query}", base_url="https://clue.invalid")
    assert response.status_code == 302
    return {key: values[0] for key, values in parse_qs(urlsplit(response.location).query).items()}


def callback(oidc, params, client=None):
    return (client or oidc.client).get("/api/v1/auth/login?" + urlencode(params), base_url="https://clue.invalid")


def test_oidc_initiation_ignores_browser_supplied_nonce(oidc):
    params = begin_login(oidc, query="provider=local&nonce=attacker-chosen")

    assert params["nonce"] != "attacker-chosen"
    assert len(params["nonce"]) >= 20
    with oidc.client.session_transaction(base_url="https://clue.invalid") as session:
        stored = session[f"_state_local_{params['state']}"]["data"]
    assert stored["nonce"] == params["nonce"]


def test_oidc_login_succeeds_with_server_nonce(oidc):
    params = begin_login(oidc)
    oidc.exchange.return_value = oidc.token(params["nonce"])

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})

    assert response.status_code == 200
    assert response.json["api_response"]["user"]["uname"] == "local-user"
    assert oidc.exchange.call_count == 1


def test_oidc_legacy_client_nonce_parameters_are_ignored(oidc):
    params = begin_login(oidc, query="oauth_provider=local&nonce=legacy-ui-nonce")
    oidc.exchange.return_value = oidc.token(params["nonce"])

    response = callback(
        oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"], "nonce": "legacy-ui-nonce"}
    )

    assert response.status_code == 200


def test_oidc_rejects_code_injected_with_attacker_shared_nonce(oidc):
    params = begin_login(oidc, query="provider=local&nonce=shared-attacker-nonce")
    # The victim's code was issued for an authorization request carrying the attacker's chosen nonce
    oidc.exchange.return_value = oidc.token("shared-attacker-nonce")

    response = callback(
        oidc,
        {"provider": "local", "code": "victim-code", "state": params["state"], "nonce": "shared-attacker-nonce"},
    )

    assert response.status_code == 401


@pytest.mark.parametrize("case", ["wrong_nonce", "missing_nonce", "bad_signature"])
def test_oidc_invalid_identity_token_is_controlled_401(oidc, case):
    params = begin_login(oidc)
    nonce = {"wrong_nonce": "other-nonce", "missing_nonce": None}.get(case, params["nonce"])
    key = JsonWebKey.generate_key("RSA", 2048, is_private=True) if case == "bad_signature" else None
    oidc.exchange.return_value = oidc.token(nonce, key)

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})

    assert response.status_code == 401
    assert params["nonce"] not in response.get_data(as_text=True)


@pytest.mark.parametrize("case", ["forged", "missing", "foreign_session", "reused"])
def test_oidc_state_validation_remains_strict(oidc, case):
    params = begin_login(oidc)
    oidc.exchange.return_value = oidc.token(params["nonce"])
    request_params = {"provider": "local", "code": "synthetic-code", "state": params["state"]}
    client = None
    if case == "forged":
        request_params["state"] = "forged-state"
    elif case == "missing":
        request_params.pop("state")
    elif case == "foreign_session":
        client = oidc.app.test_client()
    elif case == "reused":
        assert callback(oidc, request_params).status_code == 200
        oidc.exchange.reset_mock()

    response = callback(oidc, request_params, client)

    assert response.status_code == 401
    assert not oidc.exchange.called


def test_oidc_refresh_ignores_query_nonce(oidc):
    oidc.exchange.return_value = oidc.token()

    response = oidc.client.post(
        "/api/v1/auth/login?nonce=untrusted",
        json={"provider": "local", "refresh_token": "refresh-credential"},
        base_url="https://clue.invalid",
    )

    assert response.status_code == 200
    assert response.json["api_response"]["user"]["uname"] == "local-user"


def test_oidc_refresh_rejects_invalid_identity_token(oidc):
    oidc.exchange.return_value = oidc.token(key=JsonWebKey.generate_key("RSA", 2048, is_private=True))

    response = oidc.client.post(
        "/api/v1/auth/login",
        json={"provider": "local", "refresh_token": "refresh-credential"},
        base_url="https://clue.invalid",
    )

    assert response.status_code == 401


def test_login_rejects_unverified_identity_token_from_code_flow():
    app = Flask(__name__)
    provider = Mock(client_id="client", client_secret="secret")
    provider.authorize_access_token.return_value = {"access_token": "access-token", "id_token": "unverified"}
    oauth = Mock()
    oauth.create_client.return_value = provider
    app.extensions["authlib.integrations.flask_client"] = oauth
    oauth_config = SimpleNamespace(
        enabled=True,
        providers={"keycloak": SimpleNamespace(client_id="client", client_secret="secret")},
    )

    with (
        app.test_request_context("/api/v1/auth/login?provider=keycloak&code=code&nonce=attacker"),
        patch.object(config.auth, "oauth", oauth_config),
        patch.object(auth_api.user_service, "parse_user_data") as parse_user_data,
    ):
        response = auth_api.login()

    assert response.status_code == 401
    assert not parse_user_data.called
    assert not provider.parse_id_token.called


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


def test_login_rejects_invalid_normalized_user_data():
    app = Flask(__name__)
    provider = Mock(client_id="client", client_secret="secret")
    provider.authorize_access_token.return_value = {"access_token": "access-token"}
    oauth = Mock()
    oauth.create_client.return_value = provider
    app.extensions["authlib.integrations.flask_client"] = oauth
    oauth_config = SimpleNamespace(
        enabled=True,
        providers={"keycloak": SimpleNamespace(client_id="client", client_secret="secret")},
    )

    with pytest.raises(ValidationError) as validation_error:
        AuthUser.model_validate({})

    with (
        app.test_request_context("/api/v1/auth/login?provider=keycloak&code=code"),
        patch.object(config.auth, "oauth", oauth_config),
        patch.object(auth_api.user_service, "parse_user_data", side_effect=validation_error.value),
    ):
        response = auth_api.login()

    assert response.status_code == 401
    assert response.json["api_error_message"] == "The OAuth provider returned invalid user information."


def test_parse_user_data_allows_identity_without_email():
    app = Flask(__name__)
    oauth = Mock()
    oauth.create_client.return_value = Mock()
    app.extensions["authlib.integrations.flask_client"] = oauth
    provider_config = SimpleNamespace(required_groups=[], classification_map={})
    normalized_user = {
        "access": True,
        "uname": "analyst",
        "name": "Analyst",
        "email": None,
        "classification": "TLP:CLEAR",
        "groups": [],
        "roles": {UserRole.USER},
        "avatar": None,
    }

    with (
        app.test_request_context("/"),
        patch.object(config.auth.oauth, "providers", {"keycloak": provider_config}),
        patch.object(user_service, "parse_profile", return_value=normalized_user),
    ):
        result = user_service.parse_user_data({"userinfo": {}}, "keycloak")

    assert result.uname == "analyst"
    assert result.email is None


def test_validate_apikey_uses_constant_time_secret_comparison():
    app = Flask(__name__)
    auth_config = SimpleNamespace(
        allow_apikeys=True,
        apikeys={"test-key": APIKeyConf(secret="expected-secret")},
    )

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


def test_validate_apikey_adds_user_role_to_admin_key():
    app = Flask(__name__)
    auth_config = SimpleNamespace(
        allow_apikeys=True,
        apikeys={"admin-key": APIKeyConf(secret="expected-secret", roles={UserRole.ADMIN})},
    )

    with (
        app.test_request_context(
            headers={
                "X-USERID": "administrator",
                "X-CLASSIFICATION": "TLP:CLEAR",
            }
        ),
        patch.object(config, "auth", auth_config),
    ):
        result = auth_service.validate_apikey("admin-key", "expected-secret")

    assert result.user.roles == {UserRole.USER, UserRole.ADMIN}


def test_basic_auth_rejects_credentials_without_separator():
    with pytest.raises(InvalidDataException, match="key_name:key_secret"):
        auth_service.basic_auth("malformed", is_base64=False)


def test_check_obo_fails_closed_when_service_account_token_is_unavailable():
    source = ExternalSource(name="test", url="http://plugin/", obo_target="test-service")

    with patch.object(auth_service.jwt_service, "fetch_sa_token", return_value=None):
        access_token, error = auth_service.check_obo(source, "api-key-credentials", "analyst")

    assert access_token is None
    assert error == "Valid access token not provided."


def test_check_obo_accepts_token_already_scoped_for_target():
    source = ExternalSource(name="test", url="http://plugin/", obo_target="test-service")
    obo_targets = {"test-service": SimpleNamespace(scope="target-service/read")}

    with (
        patch.object(config.api, "obo_targets", obo_targets),
        patch.object(auth_service.jwt_service, "extract_audience", return_value=["target-service"]),
        patch.object(auth_service.jwt_service, "get_provider", return_value="provider"),
        patch.object(auth_service.jwt_service, "get_audience", return_value="clue-audience"),
    ):
        access_token, error = auth_service.check_obo(source, "header.payload.signature", "analyst")

    assert access_token is None
    assert error is None
