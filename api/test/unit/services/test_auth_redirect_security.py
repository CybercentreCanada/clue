from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import urlencode

import pytest
from flask import Flask

import clue.api.v1.auth as auth_api
from clue.config import config
from clue.models.config import API

EVIL_REFERER = "https://evil.attacker.example:4444/lure"
HOSTILE_HEADERS = {
    "Host": "evil.attacker.example:4444",
    "X-Forwarded-Host": "evil.attacker.example",
    "X-Forwarded-Proto": "http",
    "X-Forwarded-Port": "4444",
    "Forwarded": "host=evil.attacker.example;proto=http",
    "Origin": "https://evil.attacker.example:4444",
}


def start_login(frontend_url: str | None, headers: dict[str, str] | None = None, provider_name: str = "keycloak"):
    """Run the initial (no code) login request and return the redirect_uri given to the provider."""
    app = Flask(__name__)
    provider = Mock(client_id="client", client_secret="secret")
    oauth = Mock()
    oauth.create_client.return_value = provider
    app.extensions["authlib.integrations.flask_client"] = oauth
    oauth_config = SimpleNamespace(enabled=True, providers={provider_name: SimpleNamespace()})

    with (
        app.test_request_context(f"/api/v1/auth/login?{urlencode({'provider': provider_name})}", headers=headers or {}),
        patch.object(config.auth, "oauth", oauth_config),
        patch.object(config.api, "frontend_url", frontend_url),
    ):
        response = auth_api.login()

    return provider, response


@pytest.mark.parametrize("frontend_url", ["https://clue.example", "https://clue.example/"])
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Referer": EVIL_REFERER},
        {"Referer": "not a url at all"},
        {"Referer": "http://[::1"},
        {"Referer": "javascript:alert(1)"},
        {"Referer": EVIL_REFERER, **HOSTILE_HEADERS},
        HOSTILE_HEADERS,
    ],
)
def test_login_redirect_uri_only_uses_frontend_url(frontend_url, headers):
    provider, _ = start_login(frontend_url, headers)

    provider.authorize_redirect.assert_called_once()
    redirect_uri = provider.authorize_redirect.call_args.kwargs["redirect_uri"]

    assert redirect_uri == "https://clue.example/login?provider=keycloak"
    assert "evil" not in redirect_uri


def test_login_redirect_uri_encodes_provider():
    provider, _ = start_login("https://clue.example", provider_name="a&b=c")

    assert (
        provider.authorize_redirect.call_args.kwargs["redirect_uri"] == "https://clue.example/login?provider=a%26b%3Dc"
    )


@pytest.mark.parametrize("configured", ["https://clue.example:8443", "https://clue.example:8443/"])
def test_login_redirect_uri_from_validated_config_keeps_scheme_host_port(configured):
    provider, _ = start_login(API(frontend_url=configured).frontend_url, {"Referer": EVIL_REFERER, **HOSTILE_HEADERS})

    assert provider.authorize_redirect.call_args.kwargs["redirect_uri"] == (
        "https://clue.example:8443/login?provider=keycloak"
    )


@pytest.mark.parametrize("frontend_url", [None, ""])
def test_login_fails_safely_without_frontend_url(frontend_url):
    provider, response = start_login(frontend_url, {"Referer": EVIL_REFERER})

    provider.authorize_redirect.assert_not_called()
    assert response.status_code == 500
