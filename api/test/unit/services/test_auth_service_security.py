from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import requests
from flask import Flask
from pydantic import ValidationError

import clue.api.v1.auth as auth_api
import clue.common.logging.audit as audit_logging
import clue.helper.obo as obo_helper
import clue.security.obo as obo_security
import clue.services.auth_service as auth_service
import clue.services.user_service as user_service
from clue.common.exceptions import AccessDeniedException, ClueRuntimeError, InvalidDataException
from clue.config import CLASSIFICATION, config
from clue.models.auth_user import APIKeyConf, AuthUser, UserRole
from clue.models.config import Auth, ExternalSource


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
    auth_config = Auth(
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


def _apikey_request(headers: dict[str, str], clearance=CLASSIFICATION.RESTRICTED, roles=None):
    auth_config = Auth(
        allow_apikeys=True,
        apikeys={
            "automation-key": "legacy-secret",
            "admin-key": APIKeyConf(secret="admin-secret", roles=roles or set()),
        },
    )
    clearance_mock = (
        patch.object(user_service, "get_user_clearance", side_effect=clearance)
        if isinstance(clearance, Exception)
        else patch.object(user_service, "get_user_clearance", return_value=clearance)
    )

    with (
        Flask(__name__).test_request_context(headers=headers),
        patch.object(config, "auth", auth_config),
        clearance_mock as get_user_clearance,
    ):
        if roles:
            return auth_service.validate_apikey("admin-key", "admin-secret"), get_user_clearance
        return auth_service.validate_apikey("automation-key", "legacy-secret"), get_user_clearance


def test_validate_apikey_adds_user_role_to_admin_key():
    result, _ = _apikey_request(
        {"X-USERID": "analyst", "X-CLASSIFICATION": CLASSIFICATION.UNRESTRICTED}, roles={UserRole.ADMIN}
    )

    assert result.user.roles == {UserRole.USER, UserRole.ADMIN}


def test_legacy_key_acts_for_user_at_or_below_user_clearance():
    for classification in (CLASSIFICATION.RESTRICTED, CLASSIFICATION.UNRESTRICTED.lower()):
        result, get_user_clearance = _apikey_request(
            {
                "X-USERID": "analyst",
                "X-CLASSIFICATION": classification,
                "X-USERNAME": "Analyst",
                "X-EMAIL": "analyst@example.com",
            }
        )

        get_user_clearance.assert_called_once_with("analyst")
        assert result.user.uname == "analyst"
        assert result.user.name == "Analyst"
        assert result.user.email == "analyst@example.com"
        assert result.user.classification == CLASSIFICATION.normalize_classification(
            classification, skip_auto_select=True
        )
        assert result.user.apikey == "automation-key"


def test_validate_apikey_caps_classification_above_user_clearance():
    result, _ = _apikey_request(
        {"X-USERID": "analyst", "X-CLASSIFICATION": CLASSIFICATION.RESTRICTED},
        clearance=CLASSIFICATION.UNRESTRICTED,
    )

    assert result.user.classification == CLASSIFICATION.UNRESTRICTED
    assert CLASSIFICATION.is_accessible(CLASSIFICATION.UNRESTRICTED, result.user.classification)


def test_validate_apikey_caps_to_what_request_and_clearance_share():
    requested = CLASSIFICATION.max_classification(CLASSIFICATION.RESTRICTED, CLASSIFICATION.UNRESTRICTED)
    clearance = CLASSIFICATION.UNRESTRICTED

    result, _ = _apikey_request({"X-USERID": "analyst", "X-CLASSIFICATION": requested}, clearance=clearance)

    assert CLASSIFICATION.is_accessible(clearance, result.user.classification)
    assert CLASSIFICATION.is_accessible(requested, result.user.classification)


def test_validate_apikey_propagates_clearance_lookup_failures():
    for error in (AccessDeniedException("X-USERID does not match an active user."), ClueRuntimeError("down")):
        with pytest.raises(type(error)):
            _apikey_request({"X-USERID": "ghost", "X-CLASSIFICATION": CLASSIFICATION.UNRESTRICTED}, clearance=error)


def test_validate_apikey_rejects_invalid_classification():
    with pytest.raises(AccessDeniedException, match="invalid classification"):
        _apikey_request({"X-USERID": "analyst", "X-CLASSIFICATION": "NOT//A//CLASSIFICATION"})


def test_validate_apikey_requires_userid_and_classification():
    for headers in ({}, {"X-USERNAME": "Analyst"}, {"X-USERID": "analyst"}):
        with pytest.raises(AccessDeniedException, match="X-USERID and X-CLASSIFICATION"):
            _apikey_request(headers)


def _keycloak_provider(**overrides):
    values = {
        "admin_api_url": "https://keycloak/admin/realms/clue/",
        "classification_map": {"/secret-analysts": CLASSIFICATION.RESTRICTED},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _clearance_config(provider):
    return (
        patch.object(
            config.auth,
            "service_account",
            SimpleNamespace(enabled=True, accounts=[SimpleNamespace(provider="keycloak")]),
        ),
        patch.object(config.auth.oauth, "providers", {"keycloak": provider}),
    )


def _response(payload):
    response = Mock()
    response.json.return_value = payload
    return response


def test_get_user_clearance_maps_keycloak_groups():
    provider = _keycloak_provider()
    sa_config, providers = _clearance_config(provider)
    users = _response([{"id": "user/1", "username": "Analyst", "enabled": True}])
    groups = _response([{"name": "secret-analysts", "path": "/secret-analysts"}])

    with (
        sa_config,
        providers,
        patch.object(user_service.jwt_service, "fetch_sa_token", return_value="sa-token"),
        patch.object(user_service.requests, "get", side_effect=[users, groups]) as get,
    ):
        assert user_service.get_user_clearance("analyst") == CLASSIFICATION.RESTRICTED

    assert get.call_args_list[0].args == ("https://keycloak/admin/realms/clue/users",)
    assert get.call_args_list[0].kwargs["params"] == {"username": "analyst", "exact": "true"}
    assert get.call_args_list[0].kwargs["headers"] == {"Authorization": "Bearer sa-token"}
    assert get.call_args_list[1].args == ("https://keycloak/admin/realms/clue/users/user%2F1/groups",)


def test_get_user_clearance_defaults_to_lowest_without_mapped_group():
    sa_config, providers = _clearance_config(_keycloak_provider())
    users = _response([{"id": "1", "username": "analyst", "enabled": True}])

    with (
        sa_config,
        providers,
        patch.object(user_service.jwt_service, "fetch_sa_token", return_value="sa-token"),
        patch.object(user_service.requests, "get", side_effect=[users, _response([{"name": "other"}])]),
    ):
        assert user_service.get_user_clearance("analyst") == CLASSIFICATION.UNRESTRICTED


@pytest.mark.parametrize(
    "users",
    [
        [],
        [{"id": "1", "username": "analyst", "enabled": False}],
        [{"id": "1", "username": "analyst2", "enabled": True}],
    ],
)
def test_get_user_clearance_rejects_unknown_or_disabled_users(users):
    sa_config, providers = _clearance_config(_keycloak_provider())

    with (
        sa_config,
        providers,
        patch.object(user_service.jwt_service, "fetch_sa_token", return_value="sa-token"),
        patch.object(user_service.requests, "get", return_value=_response(users)),
        pytest.raises(AccessDeniedException, match="active user"),
    ):
        user_service.get_user_clearance("analyst")


@pytest.mark.parametrize(
    "provider,sa_token,get_error",
    [
        (_keycloak_provider(admin_api_url=None), "sa-token", None),
        (_keycloak_provider(classification_map={}), "sa-token", None),
        (_keycloak_provider(), None, None),
        (_keycloak_provider(), "sa-token", requests.Timeout("timeout")),
    ],
)
def test_get_user_clearance_fails_closed(provider, sa_token, get_error):
    sa_config, providers = _clearance_config(provider)

    with (
        sa_config,
        providers,
        patch.object(user_service.jwt_service, "fetch_sa_token", return_value=sa_token),
        patch.object(user_service.requests, "get", side_effect=get_error) as get,
        pytest.raises(ClueRuntimeError, match="Unable to verify the clearance"),
    ):
        user_service.get_user_clearance("analyst")

    if provider.admin_api_url is None or not provider.classification_map or sa_token is None:
        get.assert_not_called()


def test_get_obo_access_token_never_forwards_api_key_credentials():
    app = Flask(__name__)
    source = ExternalSource(name="test", url="http://plugin/")
    user = {"uname": "analyst", "apikey": "delegate-key"}

    with (
        app.test_request_context(headers={"Authorization": "Basic ZGVsZWdhdGUta2V5OnNlY3JldA=="}),
        patch.object(obo_helper.auth_service, "check_obo", return_value=(None, None)) as check_obo,
    ):
        access_token, obo_access_token = obo_helper.get_obo_access_token(source, user)

    assert access_token is None
    assert obo_access_token is None
    check_obo.assert_called_once_with(
        source, "ZGVsZWdhdGUta2V5OnNlY3JldA==", "analyst", cache_user="apikey:delegate-key:analyst"
    )


def test_get_obo_access_token_forwards_oauth_tokens():
    app = Flask(__name__)
    source = ExternalSource(name="test", url="http://plugin/")
    user = {"uname": "analyst", "apikey": None}

    with (
        app.test_request_context(headers={"Authorization": "Bearer header.payload.signature"}),
        patch.object(obo_helper.auth_service, "check_obo", return_value=(None, None)) as check_obo,
    ):
        access_token, _ = obo_helper.get_obo_access_token(source, user)

    assert access_token == "header.payload.signature"
    check_obo.assert_called_once_with(source, "header.payload.signature", "analyst", cache_user="analyst")


def test_get_obo_token_scopes_cache_to_cache_user():
    obo_targets = {"target": SimpleNamespace(scope="target/read")}

    with (
        patch.object(config.api, "obo_targets", obo_targets),
        patch.object(obo_security, "_get_token_raw", return_value=None) as get_token_raw,
        patch.object(obo_security, "_get_obo_token_store") as get_store,
        patch.object(
            obo_security,
            "get_extensions",
            return_value=[SimpleNamespace(modules=SimpleNamespace(obo_module=lambda *_: "obo-token"))],
        ),
    ):
        result = obo_security.get_obo_token("target", "sa-token", "analyst", cache_user="apikey:key:analyst")

    assert result == "obo-token"
    get_token_raw.assert_called_once_with("target", "apikey:key:analyst")
    get_store.assert_called_once_with("target", "apikey:key:analyst")


def test_audit_attributes_impersonated_api_key_requests():
    user = {
        "uname": "analyst",
        "classification": CLASSIFICATION.UNRESTRICTED,
        "apikey": "delegate-key",
    }

    with (
        Flask(__name__).test_request_context(),
        patch.object(audit_logging, "DEBUG", False),
        patch.object(audit_logging, "AUDIT_LOG") as audit_log,
    ):
        audit_logging.audit([], {}, user, test_audit_attributes_impersonated_api_key_requests)

    assert audit_log.info.call_args.kwargs["extra"]["user"] == "apikey:delegate-key on behalf of analyst"


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
