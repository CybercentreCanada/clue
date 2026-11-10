import base64
import hashlib
import json
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest
import requests
from authlib.jose import JsonWebKey, jwt
from flask import Flask
from pydantic import ValidationError

import clue.api.v1.auth as auth_api
import clue.security.oidc as oidc_module
import clue.services.auth_service as auth_service
import clue.services.user_service as user_service
from clue.common.exceptions import AccessDeniedException, InvalidDataException
from clue.config import config
from clue.models.auth_user import APIKeyConf, AuthUser, UserRole
from clue.models.config import ExternalSource, OAuthProvider
from clue.security.oidc import ClueOAuth2App, build_oauth, provider_client_kwargs

ISSUER = "https://provider.invalid/realms/local"
CLIENT_ID = "local-client"
JWKS_URI = "https://provider.invalid/keys"
BASE_URL = "https://clue.invalid"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"


def _provider_config(**overrides):
    values = {
        "client_id": CLIENT_ID,
        "client_secret": "local-test-only",
        "authorize_url": "https://provider.invalid/authorize",
        "access_token_url": "https://provider.invalid/token",
        "api_base_url": None,
        "audience": CLIENT_ID,
        "scope": "openid email profile",
        "iss": ISSUER,
        "jwks_uri": JWKS_URI,
    }
    values.update(overrides)
    return OAuthProvider(**values)


def _make_oidc(monkeypatch, **provider_overrides):
    """Real Flask session, real Clue provider registration and Authlib client; only the IdP endpoints are faked."""
    app = Flask("clue_010_oidc")
    app.config.update(TESTING=True, SECRET_KEY="local-test-only", SESSION_COOKIE_SECURE=True)
    app.register_blueprint(auth_api.auth_api)
    provider_config = _provider_config(**provider_overrides)
    build_oauth({"local": provider_config}).init_app(app)
    with app.app_context():
        provider = app.extensions["authlib.integrations.flask_client"].create_client("local")
    signing_key = JsonWebKey.generate_key("RSA", 2048, is_private=True, options={"kid": "local-key"})
    published = {"keys": [signing_key.as_dict(is_private=False)]}
    provider.server_metadata["jwks"] = published
    monkeypatch.setattr(
        config.auth,
        "oauth",
        SimpleNamespace(
            enabled=True,
            gravatar_enabled=False,
            jwks_refresh_cooldown_seconds=60,
            providers={"local": provider_config},
        ),
    )
    monkeypatch.setattr(config.api, "frontend_url", BASE_URL)

    jwks_fetches = []
    network = SimpleNamespace(jwks_failure=None, jwks_timeouts=[])

    def fake_network(_session, method, url, *args, **kwargs):
        if method == "GET" and url == JWKS_URI:
            jwks_fetches.append(url)
            network.jwks_timeouts.append(kwargs.get("timeout"))
            if network.jwks_failure is not None:
                raise network.jwks_failure
            return SimpleNamespace(json=lambda: published, raise_for_status=lambda: None)
        raise AssertionError("Network forbidden")

    monkeypatch.setattr("requests.sessions.Session.request", fake_network)
    exchange = Mock()
    monkeypatch.setattr(provider, "fetch_access_token", exchange)

    def token(nonce=None, key=None, kid="local-key", alg="RS256", drop=(), **claims_overrides):
        now = int(time.time())
        claims = {
            "iss": ISSUER,
            "sub": "local-user",
            "aud": CLIENT_ID,
            "exp": now + 300,
            "iat": now,
            "preferred_username": "local-user",
        }
        if nonce is not None:
            claims["nonce"] = nonce
        claims.update(claims_overrides)
        for claim in drop:
            claims.pop(claim, None)
        header = {"alg": alg}
        if kid is not None:
            header["kid"] = kid
        return {
            "access_token": "synthetic-access",
            "refresh_token": "synthetic-refresh",
            "id_token": jwt.encode(header, claims, key or signing_key).decode(),
        }

    return SimpleNamespace(
        app=app,
        client=app.test_client(),
        provider=provider,
        exchange=exchange,
        token=token,
        published=published,
        jwks_fetches=jwks_fetches,
        network=network,
    )


@pytest.fixture
def oidc(monkeypatch):
    return _make_oidc(monkeypatch)


def begin_login(oidc, client=None, query="provider=local"):
    response = (client or oidc.client).get(f"{LOGIN}?{query}", base_url=BASE_URL)
    assert response.status_code == 302
    return {key: values[0] for key, values in parse_qs(urlsplit(response.location).query).items()}


def callback(oidc, params, client=None):
    query = urlencode(params, doseq=True)
    return (client or oidc.client).get(f"{LOGIN}?{query}", base_url=BASE_URL)


def refresh(oidc, body, query=""):
    return oidc.client.post(f"{REFRESH}{query}", json=body, base_url=BASE_URL)


def assert_no_secrets(response, *secrets):
    body = response.get_data(as_text=True)
    for secret in ("synthetic-access", "synthetic-refresh", "Traceback", *secrets):
        assert secret not in body


# --- Provider registration ---------------------------------------------------------------------------------------


def test_registration_maps_configured_iss_to_trusted_issuer_metadata():
    kwargs = provider_client_kwargs("local", _provider_config())

    assert kwargs["issuer"] == ISSUER
    assert "iss" not in kwargs
    assert "auto_create" not in kwargs
    assert kwargs["client_id"] == CLIENT_ID
    assert kwargs["client_kwargs"] == {"code_challenge_method": "S256", "default_timeout": 10}


def test_token_endpoint_requests_have_a_timeout(monkeypatch):
    app = Flask("clue_token_timeout")
    build_oauth({"local": _provider_config()}).init_app(app)
    with app.app_context():
        provider = app.extensions["authlib.integrations.flask_client"].create_client("local")
    requests_sent = []

    def fake_network(_session, method, url, *args, **kwargs):
        requests_sent.append((method, url, kwargs.get("timeout")))
        return SimpleNamespace(
            status_code=200,
            headers={},
            json=lambda: {"access_token": "synthetic-access", "token_type": "Bearer"},
            raise_for_status=lambda: None,
        )

    monkeypatch.setattr("requests.sessions.Session.request", fake_network)
    with app.test_request_context():
        provider.fetch_access_token(code="synthetic-code", redirect_uri=f"{BASE_URL}/login?provider=local")

    assert requests_sent == [("POST", "https://provider.invalid/token", 10)]


def test_registered_clients_use_strict_oidc_client(oidc):
    assert isinstance(oidc.provider, ClueOAuth2App)


# --- Login initiation --------------------------------------------------------------------------------------------


def test_oidc_initiation_generates_server_side_nonce_bound_to_session(oidc):
    params = begin_login(oidc)

    assert len(params["nonce"]) >= 20
    with oidc.client.session_transaction(base_url=BASE_URL) as session:
        stored = session[f"_state_local_{params['state']}"]["data"]
    assert stored["nonce"] == params["nonce"]


@pytest.mark.parametrize("extra", ["state", "refresh_token", "redirect_uri", "unexpected"])
def test_oidc_initiation_rejects_parameters_outside_allowlist(oidc, extra):
    response = oidc.client.get(f"{LOGIN}?provider=local&{extra}=attacker-chosen", base_url=BASE_URL)

    # "state" turns the request into a callback; it is then rejected for lacking a code instead of starting a login.
    assert response.status_code in (400, 401)
    assert response.status_code != 302
    with oidc.client.session_transaction(base_url=BASE_URL) as session:
        assert not [key for key in session.keys() if key.startswith("_state_")]
    assert not oidc.exchange.called


def test_oidc_rejects_conflicting_provider_parameters(oidc):
    response = oidc.client.get(f"{LOGIN}?provider=local&oauth_provider=other", base_url=BASE_URL)

    assert response.status_code == 400


def test_oidc_rejects_unknown_provider(oidc):
    response = oidc.client.get(f"{LOGIN}?provider=unknown", base_url=BASE_URL)

    assert response.status_code == 400


def test_legacy_nonce_at_login_initiation_is_discarded(oidc):
    """UIs released before CLUE-010 add their own nonce to the login link; it must never become the session nonce."""
    with patch.object(oidc.provider, "authorize_redirect", wraps=oidc.provider.authorize_redirect) as authorize:
        params = begin_login(oidc, query="oauth_provider=local&nonce=legacy-browser-nonce")

    assert authorize.call_args.kwargs == {"redirect_uri": f"{BASE_URL}/login?provider=local"}
    assert params["nonce"] != "legacy-browser-nonce"
    with oidc.client.session_transaction(base_url=BASE_URL) as session:
        assert session[f"_state_local_{params['state']}"]["data"]["nonce"] == params["nonce"]

    # An ID token bound to the browser's nonce does not validate; only the nonce Authlib stored does.
    oidc.exchange.return_value = oidc.token("legacy-browser-nonce")
    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "query",
    [
        "oauth_provider=local&nonce=legacy-a&nonce=legacy-b",
        "provider=local&code=synthetic-code&state=any&nonce=legacy-a&nonce=legacy-b",
    ],
)
def test_legacy_nonce_must_be_single_valued(oidc, query):
    response = oidc.client.get(f"{LOGIN}?{query}", base_url=BASE_URL)

    assert response.status_code == 400
    with oidc.client.session_transaction(base_url=BASE_URL) as session:
        assert not [key for key in session.keys() if key.startswith("_state_")]
    assert not oidc.exchange.called


# --- Authorization-code callback ----------------------------------------------------------------------------------


def test_oidc_login_succeeds_with_server_nonce(oidc):
    params = begin_login(oidc)
    oidc.exchange.return_value = oidc.token(params["nonce"])

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})

    assert response.status_code == 200
    assert response.json["api_response"]["user"]["uname"] == "local-user"
    assert oidc.exchange.call_count == 1
    assert oidc.exchange.call_args.kwargs["code"] == "synthetic-code"
    assert "grant_type" not in oidc.exchange.call_args.kwargs
    assert "refresh_token" not in oidc.exchange.call_args.kwargs


@pytest.mark.parametrize("scope", ["openid email profile", "email profile"])
def test_login_uses_s256_pkce_bound_to_session(monkeypatch, scope):
    oidc = _make_oidc(monkeypatch, scope=scope)
    params = begin_login(oidc)
    with oidc.client.session_transaction(base_url=BASE_URL) as session:
        verifier = session[f"_state_local_{params['state']}"]["data"]["code_verifier"]
    expected_challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    oidc.exchange.return_value = (
        oidc.token(params["nonce"])
        if "openid" in scope
        else {"access_token": "synthetic-access", "userinfo": {"sub": "local-user", "preferred_username": "local-user"}}
    )

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})

    assert params["code_challenge_method"] == "S256"
    assert params["code_challenge"] == expected_challenge
    assert len(verifier) >= 43
    assert response.status_code == 200
    assert oidc.exchange.call_args.kwargs["code_verifier"] == verifier
    assert oidc.exchange.call_args.kwargs["redirect_uri"] == f"{BASE_URL}/login?provider=local"


def test_oidc_login_accepts_provider_informational_callback_parameters(oidc):
    params = begin_login(oidc, query="oauth_provider=local")
    oidc.exchange.return_value = oidc.token(params["nonce"])

    response = callback(
        oidc,
        {
            "provider": "local",
            "code": "synthetic-code",
            "state": params["state"],
            "session_state": "provider-session",
            "iss": ISSUER,
        },
    )

    assert response.status_code == 200


@pytest.mark.parametrize("iss", ["https://attacker.invalid", f"{ISSUER}/", ""])
def test_oidc_callback_from_untrusted_issuer_is_rejected_before_exchange(oidc, iss):
    """RFC 9207 mix-up defence: the iss authorization-response parameter must name the trusted issuer."""
    params = begin_login(oidc)
    oidc.exchange.return_value = oidc.token(params["nonce"])

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"], "iss": iss})

    assert response.status_code == 401
    assert not oidc.exchange.called
    assert_no_secrets(response, "synthetic-code", params["state"])


def test_callback_iss_is_ignored_when_no_issuer_is_configured(monkeypatch):
    oidc = _make_oidc(monkeypatch, scope="email profile", iss=None)
    params = begin_login(oidc)
    oidc.exchange.return_value = {
        "access_token": "synthetic-access",
        "userinfo": {"sub": "local-user", "preferred_username": "local-user"},
    }

    response = callback(
        oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"], "iss": "https://any.invalid"}
    )

    assert response.status_code == 200


@pytest.mark.parametrize("failure", [requests.Timeout(), requests.ConnectionError(), requests.HTTPError()])
def test_token_exchange_network_failure_is_a_controlled_502(oidc, failure):
    params = begin_login(oidc)
    oidc.exchange.side_effect = failure

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})

    assert response.status_code == 502
    assert_no_secrets(response, "synthetic-code", params["state"])


def test_oidc_login_rejects_attacker_refresh_token_link_in_fresh_session(oidc):
    """The CLUE-010 bypass: a crafted callback link must not select the refresh-token grant."""
    oidc.exchange.return_value = oidc.token()

    response = oidc.client.get(
        f"{LOGIN}?provider=local&code=unused&state=forged&refresh_token=attacker-owned-refresh",
        base_url=BASE_URL,
    )

    assert response.status_code == 400
    assert not oidc.exchange.called
    assert_no_secrets(response, "attacker-owned-refresh")


@pytest.mark.parametrize(
    "injected",
    [
        {"refresh_token": "attacker-refresh"},
        {"id_token": "attacker.id.token"},
        {"access_token": "attacker-access"},
        {"grant_type": "refresh_token"},
        {"redirect_uri": "https://evil.invalid/"},
        {"unexpected": "value"},
    ],
)
def test_oidc_callback_rejects_injected_parameters_before_exchange(oidc, injected):
    params = begin_login(oidc)
    oidc.exchange.return_value = oidc.token(params["nonce"])

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"], **injected})

    assert response.status_code == 400
    assert not oidc.exchange.called
    assert_no_secrets(response, *injected.values())
    # The legitimate transaction is untouched and can still complete.
    assert callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]}).status_code == 200


@pytest.mark.parametrize("repeated", ["code", "state", "provider"])
def test_oidc_callback_rejects_repeated_parameters(oidc, repeated):
    params = begin_login(oidc)
    oidc.exchange.return_value = oidc.token(params["nonce"])
    request_params = {"provider": "local", "code": "synthetic-code", "state": params["state"]}
    request_params[repeated] = [request_params[repeated], "second-value"]

    response = callback(oidc, request_params)

    assert response.status_code == 400
    assert not oidc.exchange.called


@pytest.mark.parametrize("token_nonce", ["session", "legacy"])
def test_legacy_nonce_on_callback_is_discarded(oidc, token_nonce):
    """UIs released before CLUE-010 also send their nonce on the callback; it is never compared to the ID token."""
    params = begin_login(oidc)
    oidc.exchange.return_value = oidc.token(params["nonce"] if token_nonce == "session" else "legacy-browser-nonce")

    response = callback(
        oidc,
        {"provider": "local", "code": "synthetic-code", "state": params["state"], "nonce": "legacy-browser-nonce"},
    )

    assert response.status_code == (200 if token_nonce == "session" else 401)
    assert oidc.exchange.call_count == 1


@pytest.mark.parametrize("case", ["forged", "missing", "foreign_session", "reused", "other_provider"])
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
    elif case == "other_provider":
        request_params["provider"] = "unknown"

    response = callback(oidc, request_params, client)

    assert response.status_code in (400, 401)
    assert not oidc.exchange.called


def test_login_csrf_attacker_callback_is_rejected_in_the_victim_browser(oidc):
    """CWE-352: an attacker's own callback URL (code + state) opened by a victim must not log the victim in."""
    attacker = oidc.app.test_client()
    attacker_params = begin_login(oidc, client=attacker)
    victim_params = begin_login(oidc)
    oidc.exchange.return_value = oidc.token(attacker_params["nonce"])

    response = callback(oidc, {"provider": "local", "code": "attacker-code", "state": attacker_params["state"]})

    assert response.status_code == 401
    assert not oidc.exchange.called
    assert_no_secrets(response, "attacker-code", attacker_params["state"])
    # The victim's own pending login is unaffected and still completes with the victim's code.
    oidc.exchange.return_value = oidc.token(victim_params["nonce"])
    victim = callback(oidc, {"provider": "local", "code": "victim-code", "state": victim_params["state"]})
    assert victim.status_code == 200
    assert oidc.exchange.call_args.kwargs["code"] == "victim-code"


def test_oidc_provider_error_callback_is_controlled_and_does_not_exchange(oidc):
    params = begin_login(oidc)

    response = callback(
        oidc,
        {
            "provider": "local",
            "state": params["state"],
            "error": "access_denied",
            "error_description": "<script>reflected</script>",
        },
    )

    assert response.status_code == 401
    assert not oidc.exchange.called
    assert "reflected" not in response.get_data(as_text=True)


def _forge_unsigned(oidc, nonce):
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "kid": "local-key"}).encode()).rstrip(b"=")
    good = oidc.token(nonce)
    payload = good["id_token"].split(".")[1]
    return {**good, "id_token": f"{header.decode()}.{payload}."}


INVALID_ID_TOKENS = {
    "wrong_nonce": lambda oidc, nonce: oidc.token("other-nonce"),
    "missing_nonce": lambda oidc, nonce: oidc.token(None),
    "nonce_supported_false": lambda oidc, nonce: oidc.token("other-nonce", nonce_supported=False),
    "bad_signature": lambda oidc, nonce: oidc.token(nonce, key=JsonWebKey.generate_key("RSA", 2048, is_private=True)),
    "unknown_kid": lambda oidc, nonce: oidc.token(
        nonce, key=JsonWebKey.generate_key("RSA", 2048, is_private=True), kid="unknown-key"
    ),
    "expired": lambda oidc, nonce: oidc.token(nonce, exp=int(time.time()) - 3600, iat=int(time.time()) - 7200),
    "issued_in_future": lambda oidc, nonce: oidc.token(nonce, iat=int(time.time()) + 3600),
    "not_yet_valid": lambda oidc, nonce: oidc.token(nonce, nbf=int(time.time()) + 3600),
    "malformed": lambda oidc, nonce: {**oidc.token(nonce), "id_token": "not-a-jwt"},
    "unsigned_alg_none": _forge_unsigned,
    "wrong_issuer": lambda oidc, nonce: oidc.token(nonce, iss="https://attacker.invalid"),
    "missing_issuer": lambda oidc, nonce: oidc.token(nonce, drop=("iss",)),
    "wrong_audience": lambda oidc, nonce: oidc.token(nonce, aud="other-client"),
    "wrong_audience_with_matching_azp": lambda oidc, nonce: oidc.token(nonce, aud="other-client", azp=CLIENT_ID),
    "multiple_audiences_without_azp": lambda oidc, nonce: oidc.token(nonce, aud=[CLIENT_ID, "other-client"]),
    "foreign_azp": lambda oidc, nonce: oidc.token(nonce, azp="other-client"),
    "missing_sub": lambda oidc, nonce: oidc.token(nonce, drop=("sub",)),
    "missing_exp": lambda oidc, nonce: oidc.token(nonce, drop=("exp",)),
    "missing_iat": lambda oidc, nonce: oidc.token(nonce, drop=("iat",)),
    "bad_at_hash": lambda oidc, nonce: oidc.token(nonce, at_hash="AAAAAAAAAAAAAAAAAAAAAA"),
    "missing_id_token": lambda oidc, nonce: {"access_token": "synthetic-access", "refresh_token": "synthetic-refresh"},
    "missing_id_token_with_userinfo": lambda oidc, nonce: {
        "access_token": "synthetic-access",
        "refresh_token": "synthetic-refresh",
        "userinfo": {"sub": "forged", "preferred_username": "forged-user"},
    },
}


@pytest.mark.parametrize("case", sorted(INVALID_ID_TOKENS))
def test_oidc_invalid_identity_token_is_controlled_401(oidc, case):
    params = begin_login(oidc)
    oidc.exchange.return_value = INVALID_ID_TOKENS[case](oidc, params["nonce"])

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})

    assert response.status_code == 401
    assert "app_token" not in response.get_data(as_text=True)
    assert_no_secrets(response, params["nonce"], params["state"], "synthetic-code", "local-key", "unknown-key")


def test_oidc_validated_id_token_claims_override_token_response_userinfo(oidc):
    params = begin_login(oidc)
    oidc.exchange.return_value = {
        **oidc.token(params["nonce"]),
        "userinfo": {"sub": "forged", "preferred_username": "forged-user"},
    }

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})

    assert response.status_code == 200
    assert response.json["api_response"]["user"]["uname"] == "local-user"


def test_oidc_invalid_id_token_cannot_be_bypassed_with_userinfo(oidc):
    params = begin_login(oidc)
    oidc.exchange.return_value = {
        **oidc.token("wrong-nonce"),
        "userinfo": {"sub": "forged", "preferred_username": "forged-user"},
    }

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})

    assert response.status_code == 401
    assert_no_secrets(response, "forged-user")


def test_oidc_audience_list_with_matching_azp_is_accepted(oidc):
    params = begin_login(oidc)
    oidc.exchange.return_value = oidc.token(params["nonce"], aud=[CLIENT_ID, "other-client"], azp=CLIENT_ID)

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})

    assert response.status_code == 200


def test_oidc_unknown_kid_refreshes_jwks_once_then_fails_closed(oidc):
    params = begin_login(oidc)
    oidc.exchange.return_value = INVALID_ID_TOKENS["unknown_kid"](oidc, params["nonce"])

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})

    assert response.status_code == 401
    assert response.json["api_error_message"] == "The ID token signing key is not trusted."
    assert oidc.jwks_fetches == [JWKS_URI]


def test_oidc_rotated_signing_key_is_fetched_from_trusted_jwks(oidc):
    params = begin_login(oidc)
    rotated = JsonWebKey.generate_key("RSA", 2048, is_private=True, options={"kid": "rotated-key"})
    oidc.published["keys"] = [rotated.as_dict(is_private=False)]
    oidc.provider.server_metadata["jwks"] = {"keys": []}
    oidc.exchange.return_value = oidc.token(params["nonce"], key=rotated, kid="rotated-key")

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})

    assert response.status_code == 200
    assert oidc.jwks_fetches == [JWKS_URI]


def _clock(monkeypatch, start=1000.0):
    clock = SimpleNamespace(now=start)
    monkeypatch.setattr(oidc_module.time, "monotonic", lambda: clock.now)
    return clock


def _login_status(oidc, **token_kwargs):
    params = begin_login(oidc)
    oidc.exchange.return_value = oidc.token(params["nonce"], **token_kwargs)
    return callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})


def test_oidc_jwks_fetch_has_a_timeout(oidc):
    _login_status(oidc, key=JsonWebKey.generate_key("RSA", 2048, is_private=True), kid="unknown-key")

    assert oidc.network.jwks_timeouts == [10]


def test_oidc_unknown_kids_cannot_trigger_a_jwks_fetch_per_login(oidc, monkeypatch):
    clock = _clock(monkeypatch)
    attacker_key = JsonWebKey.generate_key("RSA", 2048, is_private=True)

    statuses = [_login_status(oidc, key=attacker_key, kid=f"unknown-{i}").status_code for i in range(3)]
    clock.now += 61
    statuses.append(_login_status(oidc, key=attacker_key, kid="unknown-after-cooldown").status_code)

    assert statuses == [401, 401, 401, 401]
    assert oidc.jwks_fetches == [JWKS_URI, JWKS_URI]


def test_oidc_cached_jwks_are_refreshed_after_the_refresh_interval(oidc, monkeypatch):
    clock = _clock(monkeypatch)
    oidc.provider.server_metadata["jwks"] = {"keys": list(oidc.published["keys"])}
    assert _login_status(oidc).status_code == 200
    assert oidc.jwks_fetches == []

    # The provider withdrew the key: once the cache is refreshed it is no longer trusted.
    oidc.published["keys"] = []
    clock.now += oidc_module.JWKS_REFRESH_AFTER_SECONDS + 1

    assert _login_status(oidc).status_code == 401
    assert oidc.jwks_fetches == [JWKS_URI]


@pytest.mark.parametrize(
    "failure", [requests.Timeout(), requests.ConnectionError(), requests.HTTPError(), ValueError("bad json")]
)
def test_oidc_failed_jwks_refresh_keeps_keys_within_max_age(oidc, monkeypatch, failure):
    clock = _clock(monkeypatch)
    assert _login_status(oidc).status_code == 200
    oidc.network.jwks_failure = failure
    clock.now += oidc_module.JWKS_REFRESH_AFTER_SECONDS + 1

    assert _login_status(oidc).status_code == 200
    assert oidc.jwks_fetches == [JWKS_URI]


def test_oidc_jwks_older_than_max_age_are_never_used(oidc, monkeypatch):
    clock = _clock(monkeypatch)
    assert _login_status(oidc).status_code == 200
    oidc.network.jwks_failure = requests.ConnectionError()
    clock.now += oidc_module.JWKS_MAX_AGE_SECONDS

    response = _login_status(oidc)

    assert response.status_code == 502
    assert response.json["api_error_message"] == "The OAuth provider could not be reached. Try again later."
    assert_no_secrets(response)


@pytest.mark.parametrize("failure", [requests.Timeout(), requests.ConnectionError(), requests.HTTPError()])
def test_oidc_jwks_fetch_failure_without_cache_is_retryable(oidc, failure):
    oidc.provider.server_metadata.pop("jwks")
    oidc.network.jwks_failure = failure

    response = _login_status(oidc)

    assert response.status_code == 502
    assert oidc.jwks_fetches == [JWKS_URI]
    assert_no_secrets(response)


def test_oidc_jwks_fetch_failure_without_cache_is_retryable_during_cooldown(oidc):
    oidc.provider.server_metadata.pop("jwks")
    oidc.network.jwks_failure = requests.Timeout()

    first = _login_status(oidc)
    second = _login_status(oidc)

    assert first.status_code == second.status_code == 502
    assert oidc.jwks_fetches == [JWKS_URI]


@pytest.mark.parametrize(
    "payload",
    [None, "text", [], {}, {"keys": "x"}, {"keys": [None, {"kty": "RSA"}]}],
    ids=["null", "text", "list", "empty", "keys_not_list", "only_invalid_keys"],
)
def test_oidc_malformed_jwks_payload_fails_closed(oidc, monkeypatch, payload):
    oidc.provider.server_metadata.pop("jwks")
    monkeypatch.setattr(
        "requests.sessions.Session.request",
        lambda *_args, **_kwargs: SimpleNamespace(json=lambda: payload, raise_for_status=lambda: None),
    )

    response = _login_status(oidc)

    assert response.status_code == 502
    assert response.json["api_error_message"] == "The OAuth provider could not be reached. Try again later."
    assert_no_secrets(response)


def test_oidc_malformed_jwks_entries_are_ignored(oidc):
    oidc.published["keys"] = [None, "text", {"kty": "RSA"}, *oidc.published["keys"]]
    oidc.provider.server_metadata.pop("jwks")

    assert _login_status(oidc).status_code == 200
    assert oidc.provider.server_metadata["jwks"]["keys"] == oidc.published["keys"][3:]


def test_oidc_rejects_id_tokens_when_no_trusted_issuer_is_configured(monkeypatch):
    oidc = _make_oidc(monkeypatch, iss=None)
    params = begin_login(oidc)
    oidc.exchange.return_value = oidc.token(params["nonce"])

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})

    assert response.status_code == 401
    assert response.json["api_error_message"] == "The OAuth provider has no trusted issuer configured."


def test_oidc_rejects_id_token_when_openid_scope_was_not_requested(monkeypatch):
    oidc = _make_oidc(monkeypatch, scope="email profile")
    params = begin_login(oidc)
    assert "nonce" not in params
    oidc.exchange.return_value = oidc.token()

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})

    assert response.status_code == 401
    assert response.json["api_error_message"] == "The OAuth provider did not return a verified identity token."


def test_oidc_rejects_unverified_id_token_with_userinfo_when_openid_was_not_requested(monkeypatch):
    oidc = _make_oidc(monkeypatch, scope="email profile")
    params = begin_login(oidc)
    oidc.exchange.return_value = {
        **oidc.token(),
        "userinfo": {"sub": "forged", "preferred_username": "forged-user"},
    }

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})

    assert response.status_code == 401
    assert response.json["api_error_message"] == "The OAuth provider did not return a verified identity token."
    assert_no_secrets(response, "forged-user")


def test_non_openid_oauth_response_with_userinfo_remains_supported(monkeypatch):
    oidc = _make_oidc(monkeypatch, scope="email profile")
    params = begin_login(oidc)
    oidc.exchange.return_value = {
        "access_token": "synthetic-access",
        "userinfo": {"sub": "local-user", "preferred_username": "local-user"},
    }

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})

    assert response.status_code == 200
    assert response.json["api_response"]["user"]["uname"] == "local-user"


def test_login_rejects_oauth_response_without_access_token(oidc):
    params = begin_login(oidc)
    token = oidc.token(params["nonce"])
    token.pop("access_token")
    oidc.exchange.return_value = token

    response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})

    assert response.status_code == 401
    assert response.json["api_error_message"] == "The OAuth provider did not return an access token."


def test_login_rejects_invalid_normalized_user_data(oidc):
    params = begin_login(oidc)
    oidc.exchange.return_value = oidc.token(params["nonce"])
    with pytest.raises(ValidationError) as validation_error:
        AuthUser.model_validate({})

    with patch.object(auth_api.user_service, "parse_user_data", side_effect=validation_error.value):
        response = callback(oidc, {"provider": "local", "code": "synthetic-code", "state": params["state"]})

    assert response.status_code == 401
    assert response.json["api_error_message"] == "The OAuth provider returned invalid user information."


# --- Refresh-token grant -----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        {"provider": "local", "refresh_token": "legacy-refresh"},
        {"oauth_provider": "local", "refresh_token": "legacy-refresh"},
        {"provider": None, "refresh_token": "legacy-refresh"},
        {"refresh_token": "legacy-refresh"},
    ],
)
def test_legacy_refresh_post_to_login_gets_401_without_exchange(oidc, body):
    """UIs released before CLUE-010 refresh through the login endpoint; they must clear their credentials instead."""
    oidc.exchange.return_value = oidc.token()

    response = oidc.client.post(LOGIN, json=body, base_url=BASE_URL)

    assert response.status_code == 401
    assert response.json["api_error_message"] == auth_api.LEGACY_REFRESH_ERROR
    assert not oidc.exchange.called
    assert_no_secrets(response, "legacy-refresh")


@pytest.mark.parametrize(
    "request_kwargs",
    [
        {"json": {"provider": "local", "code": "synthetic-code", "state": "forged"}},
        {"json": {"provider": "local", "refresh_token": "attacker-refresh", "grant_type": "refresh_token"}},
        {"json": {"provider": "local", "refresh_token": "attacker-refresh", "nonce": "attacker-nonce"}},
        {"json": {"refresh_token": "attacker-refresh"}, "query_string": {"provider": "local"}},
        {"data": {"provider": "local", "refresh_token": "attacker-refresh"}},
    ],
)
def test_login_endpoint_rejects_other_refresh_and_oauth_posts(oidc, request_kwargs):
    oidc.exchange.return_value = oidc.token()

    response = oidc.client.post(LOGIN, base_url=BASE_URL, **request_kwargs)

    assert response.status_code == 400
    assert not oidc.exchange.called


def test_refresh_endpoint_exchanges_refresh_token_and_validates_identity(oidc):
    oidc.exchange.return_value = oidc.token()

    response = refresh(oidc, {"provider": "local", "refresh_token": "refresh-credential"})

    assert response.status_code == 200
    assert response.json["api_response"]["user"]["uname"] == "local-user"
    oidc.exchange.assert_called_once()
    assert oidc.exchange.call_args.kwargs["grant_type"] == "refresh_token"
    assert oidc.exchange.call_args.kwargs["refresh_token"] == "refresh-credential"


@pytest.mark.parametrize("groups, status", [(["allowed"], 200), ([], 403)])
def test_non_openid_refresh_parses_userinfo(monkeypatch, groups, status):
    oidc = _make_oidc(monkeypatch, scope="email profile", required_groups=["allowed"])
    oidc.exchange.return_value = {
        "access_token": "synthetic-access",
        "userinfo": {"sub": "local-user", "preferred_username": "local-user", "groups": groups},
    }

    response = refresh(oidc, {"provider": "local", "refresh_token": "refresh-credential"})

    assert response.status_code == status
    if status == 200:
        assert response.json["api_response"]["user"]["uname"] == "local-user"
        assert response.json["api_response"]["user"]["groups"] == groups


@pytest.mark.parametrize(
    "case",
    [
        "bad_signature",
        "unknown_kid",
        "expired",
        "malformed",
        "wrong_issuer",
        "wrong_audience_with_matching_azp",
        "missing_id_token",
        "missing_id_token_with_userinfo",
    ],
)
def test_refresh_endpoint_rejects_invalid_identity_token(oidc, case):
    oidc.exchange.return_value = INVALID_ID_TOKENS[case](oidc, None)

    response = refresh(oidc, {"provider": "local", "refresh_token": "refresh-credential"})

    assert response.status_code == 401
    assert_no_secrets(response, "refresh-credential")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"query": "?provider=local&refresh_token=attacker-refresh", "json": None},
        {"query": "?nonce=untrusted", "json": {"provider": "local", "refresh_token": "refresh-credential"}},
        {"query": "", "json": {"provider": "local"}},
        {"query": "", "json": {"provider": "local", "refresh_token": ""}},
        {"query": "", "json": {"provider": "local", "refresh_token": 123}},
        {"query": "", "json": {"provider": "local", "refresh_token": "x", "nonce": "n"}},
        {"query": "", "json": {"provider": "unknown", "refresh_token": "refresh-credential"}},
        {"query": "", "json": ["provider", "local"]},
    ],
)
def test_refresh_endpoint_strictly_validates_input(oidc, kwargs):
    oidc.exchange.return_value = oidc.token()

    if kwargs["json"] is None:
        response = oidc.client.post(f"{REFRESH}{kwargs['query']}", base_url=BASE_URL)
    else:
        response = refresh(oidc, kwargs["json"], kwargs["query"])

    assert response.status_code == 400
    assert not oidc.exchange.called


def test_refresh_endpoint_rejects_form_posts_and_get(oidc):
    oidc.exchange.return_value = oidc.token()

    form = oidc.client.post(REFRESH, data={"provider": "local", "refresh_token": "attacker-refresh"}, base_url=BASE_URL)
    get = oidc.client.get(f"{REFRESH}?provider=local&refresh_token=attacker-refresh", base_url=BASE_URL)

    assert form.status_code == 400
    assert get.status_code == 405
    assert not oidc.exchange.called


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
