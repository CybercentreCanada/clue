import base64
import uuid
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from flask import Flask
from pydantic import ValidationError

import clue.api.v1.auth as auth_api
import clue.services.auth_service as auth_service
import clue.services.user_service as user_service
from clue.common.exceptions import AccessDeniedException, InvalidDataException, TooManyRequestsException
from clue.config import config
from clue.models.auth_user import APIKeyConf, AuthUser, UserRole
from clue.models.config import APIKeyLockout, ExternalSource
from clue.security import api_login


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


@pytest.mark.parametrize("name", ["test-key", "missing-key"])
def test_validate_apikey_rejects_wrong_secret_and_unknown_name_identically(name):
    app = Flask(__name__)
    auth_config = SimpleNamespace(
        allow_apikeys=True,
        apikeys={"test-key": APIKeyConf(secret="expected-secret")},
        apikey_lockout=APIKeyLockout(enabled=False),
    )

    with (
        app.test_request_context(headers={"X-USERID": "analyst", "X-CLASSIFICATION": "TLP:CLEAR"}),
        patch.object(config, "auth", auth_config),
        patch("clue.services.auth_service.hmac.compare_digest", return_value=False) as compare_digest,
        pytest.raises(AccessDeniedException, match="^Invalid API key$"),
    ):
        auth_service.validate_apikey(name, "provided-secret")

    compare_digest.assert_called_once()
    assert compare_digest.call_args.args[1] == b"provided-secret"


@pytest.mark.parametrize(
    "trusted_proxies,forwarded_for,expected_ip",
    [
        ([], "203.0.113.9", "10.1.1.1"),
        (["10.0.0.0/8"], "203.0.113.9, 198.51.100.7", "198.51.100.7"),
        (["10.0.0.0/8", "198.51.100.0/24"], "203.0.113.9, 198.51.100.7", "203.0.113.9"),
        (["192.0.2.0/24"], "203.0.113.9", "10.1.1.1"),
        (["10.0.0.0/8"], "not-an-ip", "10.1.1.1"),
    ],
)
def test_get_client_ip_only_trusts_forwarded_entries_from_trusted_proxies(trusted_proxies, forwarded_for, expected_ip):
    auth_config = SimpleNamespace(apikey_lockout=APIKeyLockout(trusted_proxies=trusted_proxies))

    with (
        Flask(__name__).test_request_context(
            headers={"X-Forwarded-For": forwarded_for}, environ_base={"REMOTE_ADDR": "10.1.1.1"}
        ),
        patch.object(config, "auth", auth_config),
    ):
        assert auth_service._get_client_ip() == expected_ip


def test_validate_apikey_adds_user_role_to_admin_key():
    app = Flask(__name__)
    auth_config = SimpleNamespace(
        allow_apikeys=True,
        apikeys={"admin-key": APIKeyConf(secret="expected-secret", roles={UserRole.ADMIN})},
        apikey_lockout=APIKeyLockout(enabled=False),
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


@pytest.fixture
def apikey_lockout(redis_connection):
    key_name = f"test-key-{uuid.uuid4()}"
    auth_config = SimpleNamespace(
        allow_apikeys=True,
        apikeys={key_name: APIKeyConf(secret="expected-secret")},
        apikey_lockout=APIKeyLockout(
            max_failures_per_ip=3, window_seconds=60, max_lockout_seconds=300, trusted_proxies=["127.0.0.1/32"]
        ),
    )
    used_keys: set[str] = set()
    get_keys = auth_service._apikey_lockout.keys

    def _track_keys(identifier: str) -> list[str]:
        keys = get_keys(identifier)
        used_keys.update(keys)
        return keys

    with (
        patch.object(config, "auth", auth_config),
        patch.object(auth_service._apikey_lockout, "keys", side_effect=_track_keys),
    ):
        yield SimpleNamespace(redis=redis_connection, key_name=key_name)

    if used_keys:
        redis_connection.delete(*used_keys)


def _attempt_apikey(name: str, secret: str, forwarded_for: str):
    with Flask(__name__).test_request_context(
        headers={"X-USERID": "analyst", "X-CLASSIFICATION": "TLP:CLEAR", "X-Forwarded-For": forwarded_for},
        environ_base={"REMOTE_ADDR": "127.0.0.1"},
    ):
        return auth_service.validate_apikey(name, secret)


def _lockout_state(lockout, client_ip: str) -> SimpleNamespace:
    lockout_key, failures_key, history_key = auth_service._apikey_lockout.keys(client_ip)
    return SimpleNamespace(
        lockout_key=lockout_key,
        lockout_ttl=lockout.redis.ttl(lockout_key),
        failures=int(lockout.redis.get(failures_key) or 0),
        history_key=history_key,
        history_ttl=lockout.redis.ttl(history_key),
        lockouts=int(lockout.redis.get(history_key) or 0),
    )


def _unique_ip() -> str:
    return f"10.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"


def _guess() -> str:
    return f"guess-{uuid.uuid4()}"


def _fail_until_locked_out(client_ip: str, prefix: str = "") -> None:
    for _ in range(3):
        with pytest.raises(AccessDeniedException, match="^Invalid API key$"):
            _attempt_apikey(_guess(), "wrong", f"{prefix}{client_ip}")


def test_validate_apikey_locks_out_client_ip_even_with_spoofed_forwarded_for(apikey_lockout):
    client_ip = _unique_ip()
    _fail_until_locked_out(client_ip, prefix="203.0.113.1, ")

    with pytest.raises(TooManyRequestsException):
        _attempt_apikey(apikey_lockout.key_name, "expected-secret", f"198.51.100.1, {client_ip}")
    assert _attempt_apikey(apikey_lockout.key_name, "expected-secret", _unique_ip()).user.uname == "analyst"


def test_validate_apikey_attempts_while_locked_out_are_not_counted_whatever_the_secret(apikey_lockout):
    client_ip = _unique_ip()
    _fail_until_locked_out(client_ip)
    before = _lockout_state(apikey_lockout, client_ip)
    apikey_lockout.redis.expire(before.lockout_key, 5)

    for secret in ["wrong", "expected-secret"] * 5:
        with pytest.raises(TooManyRequestsException):
            _attempt_apikey(apikey_lockout.key_name, secret, client_ip)

    after = _lockout_state(apikey_lockout, client_ip)
    assert 58 <= before.lockout_ttl <= 60
    assert after.lockout_ttl <= 5
    assert after.failures == 0


def test_validate_apikey_repeated_lockouts_back_off_exponentially_up_to_cap(apikey_lockout):
    client_ip = _unique_ip()
    for expected_ttl in [60, 120, 240, 300, 300]:
        _fail_until_locked_out(client_ip)
        state = _lockout_state(apikey_lockout, client_ip)
        assert expected_ttl - 2 <= state.lockout_ttl <= expected_ttl
        apikey_lockout.redis.delete(state.lockout_key)


def test_validate_apikey_lockout_history_expires_and_resets_backoff(apikey_lockout):
    client_ip = _unique_ip()
    _fail_until_locked_out(client_ip)
    first = _lockout_state(apikey_lockout, client_ip)
    assert 58 <= first.lockout_ttl <= 60
    assert 358 <= first.history_ttl <= 360
    assert first.lockouts == 1

    apikey_lockout.redis.expireat(first.lockout_key, 0)
    assert apikey_lockout.redis.get(first.history_key) is not None
    _fail_until_locked_out(client_ip)
    second = _lockout_state(apikey_lockout, client_ip)
    assert 118 <= second.lockout_ttl <= 120
    assert 418 <= second.history_ttl <= 420
    assert second.lockouts == 2

    apikey_lockout.redis.expireat(second.lockout_key, 0)
    apikey_lockout.redis.expireat(second.history_key, 0)
    assert apikey_lockout.redis.get(second.history_key) is None
    _fail_until_locked_out(client_ip)
    reset = _lockout_state(apikey_lockout, client_ip)
    assert 58 <= reset.lockout_ttl <= 60
    assert 358 <= reset.history_ttl <= 360
    assert reset.lockouts == 1


def test_validate_apikey_failures_from_many_clients_cannot_lock_out_a_key_name(apikey_lockout):
    name = apikey_lockout.key_name
    for _ in range(10):
        client_ip = _unique_ip()
        for _ in range(2):
            with pytest.raises(AccessDeniedException):
                _attempt_apikey(name, "wrong", client_ip)

    assert _attempt_apikey(name, "expected-secret", _unique_ip()).user.uname == "analyst"


def test_api_login_returns_429_when_apikey_is_locked_out(apikey_lockout):
    @api_login(audit=False)
    def endpoint(**kwargs):
        return kwargs["user"]

    client_ip = _unique_ip()
    authorization = "Basic " + base64.b64encode(f"{apikey_lockout.key_name}:wrong".encode()).decode()
    statuses = []
    for _ in range(4):
        with Flask(__name__).test_request_context(
            headers={"Authorization": authorization, "X-Forwarded-For": client_ip},
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        ):
            statuses.append(endpoint().status_code)

    assert statuses == [403, 403, 403, 429]


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
