import os

import pytest
from pydantic import ValidationError

from clue.models.auth_user import APIKeyConf, UserRole
from clue.models.config import (
    API,
    Auth,
    Config,
    OAuth,
    OAuthProvider,
    ServiceAccount,
    ServiceAccountCreds,
)


def test_oauth_provider_accepts_legacy_role_map():
    provider = OAuthProvider(
        client_id="client",
        access_token_url="https://oauth.example/token",
        authorize_url="https://oauth.example/authorize",
        api_base_url="https://oauth.example/",
        audience="clue",
        scope="openid",
        jwks_uri="https://oauth.example/jwks",
        role_map={"clue_admin": "admin"},
    )

    assert provider.role_map == {UserRole.ADMIN: "clue_admin"}


def test_oauth_provider_rejects_ambiguous_role_map():
    with pytest.raises(ValidationError, match="role_map is ambiguous"):
        OAuthProvider(
            client_id="client",
            access_token_url="https://oauth.example/token",
            authorize_url="https://oauth.example/authorize",
            api_base_url="https://oauth.example/",
            audience="clue",
            scope="openid",
            jwks_uri="https://oauth.example/jwks",
            role_map={"admin": "user"},
        )


def test_oauth_provider_ignores_unsupported_legacy_roles():
    provider = OAuthProvider(
        client_id="client",
        access_token_url="https://oauth.example/token",
        authorize_url="https://oauth.example/authorize",
        api_base_url="https://oauth.example/",
        audience="clue",
        scope="openid",
        jwks_uri="https://oauth.example/jwks",
        role_map={"clue-admins": "admin", "clue-analysts": "analyst"},
    )

    assert provider.role_map == {UserRole.ADMIN: "clue-admins"}


def test_service_account():
    with pytest.raises(ValidationError) as err:
        ServiceAccount(enabled=True, accounts=[ServiceAccountCreds(username="potato", provider="keycloak")])

    assert "password" in str(err)

    os.environ["SA_KEYCLOAK_PASSWORD"] = "potato"

    ServiceAccount(enabled=True, accounts=[ServiceAccountCreds(username="potato", provider="keycloak")])

    with pytest.raises(ValidationError) as err:
        ServiceAccount(
            enabled=True,
            accounts=[
                ServiceAccountCreds(username="potato", provider="keycloak"),
                ServiceAccountCreds(username="potato", provider="keycloak"),
            ],
        )

    assert "You may only have one service account per provider" in str(err)

    os.environ.pop("SA_KEYCLOAK_PASSWORD")


def test_auth_validation():
    with pytest.raises(ValidationError) as err:
        Auth(oauth=OAuth(enabled=False), service_account=ServiceAccount(enabled=True))

    assert "In order to use service accounts to connect to plugins" in str(err)

    with pytest.raises(ValidationError) as err:
        Auth(
            oauth=OAuth(enabled=True),
            service_account=ServiceAccount(
                enabled=True, accounts=[ServiceAccountCreds(username="potato", provider="potato", password="potato")]
            ),
        )

    assert "potato is used to connect to non-existent provider potato." in str(err)

    Auth(
        oauth=OAuth(
            enabled=True,
            providers={
                "potato": OAuthProvider(
                    client_id="potato",
                    access_token_url="potato",
                    authorize_url="potato",
                    api_base_url="potato",
                    audience="potato",
                    scope="potato",
                    jwks_uri="potato",
                )
            },
        ),
        service_account=ServiceAccount(
            enabled=True, accounts=[ServiceAccountCreds(username="potato", provider="potato", password="potato")]
        ),
    )


def test_api_key_config_rejects_empty_secret():
    for secret in ("", "   "):
        with pytest.raises(ValidationError):
            APIKeyConf(secret=secret)


def test_auth_converts_legacy_api_keys_with_warning(caplog):
    auth = Auth(apikeys={"legacy-key": "legacy-secret"})

    assert auth.apikeys == {"legacy-key": APIKeyConf(secret="legacy-secret")}
    assert "Legacy string API key configuration is deprecated" in caplog.text


def test_auth_rejects_empty_api_key_name():
    with pytest.raises(ValidationError, match="API key names must not be empty"):
        Auth(apikeys={"": "secret"})


@pytest.mark.parametrize(
    "frontend_url,expected",
    [
        (None, None),
        ("https://clue.example", "https://clue.example"),
        ("https://clue.example/", "https://clue.example"),
        ("http://localhost:3000/", "http://localhost:3000"),
        ("HTTPS://Clue.Example:8443", "https://Clue.Example:8443"),
        ("http://[::1]:3000/", "http://[::1]:3000"),
        ("http://127.0.0.1", "http://127.0.0.1"),
        ("http://clue-ui_1:3000", "http://clue-ui_1:3000"),
    ],
)
def test_api_frontend_url_accepts_valid_urls(frontend_url, expected):
    assert API(frontend_url=frontend_url).frontend_url == expected


@pytest.mark.parametrize(
    "frontend_url",
    [
        "",
        "clue.example",
        "/login",
        "//clue.example",
        "ftp://clue.example",
        "javascript:alert(1)",
        "https://",
        "https://clue.example?next=1",
        "https://clue.example/#frag",
        "https://user:pass@clue.example",
        "https://clue.example:notaport",
        "https://clue.example\\@evil.example",
        "https://clue.example /",
        # Path prefixes are unsupported: the UI is served from the root of its origin
        "https://clue.example/ui",
        "https://clue.example/ui/",
        "https://clue.example//",
        "https://clue.example/../other",
        "https://clue.example/%2e%2e/other",
        "https://clue.example/a%2Fb",
        "https://clue.example/./",
        # Control characters and malformed authorities
        "https://clue.example\x00",
        "https://clue.example\n/",
        "https://clue\t.example",
        "https://clue.example\x7f",
        "https://clue.example%2540evil.example",
        "https://clue.example%40evil.example",
        "https://clue.example%2f@evil.example",
        "https://clue.example:",
        "https://clue.example:0",
        "https://clue.example:65536",
        "https://clue.example:-1",
        "https://clue.example:80:80",
        "https://:443",
        "https://clue.example@evil.example",
        "https://@clue.example",
        "https://[::1",
        "https://[not-an-ip]",
        "https://clue..example",
        "https://.clue.example",
        "https://-clue.example",
        "https://clue.example,evil.example",
        "https://clue.example;evil.example",
        "https://cl\u00fce.example",
        "https:clue.example",
        "https:///clue.example",
    ],
)
def test_api_frontend_url_rejects_invalid_urls(frontend_url):
    with pytest.raises(ValidationError, match="frontend_url"):
        API(frontend_url=frontend_url)


def test_frontend_url_goes_through_config_loading(monkeypatch):
    monkeypatch.setenv("API__FRONTEND_URL", "https://clue.example:8443/")
    assert Config().api.frontend_url == "https://clue.example:8443"

    for bad_url in ("", "https://clue.example/ui", "https://user@clue.example", "https://clue.example\n"):
        monkeypatch.setenv("API__FRONTEND_URL", bad_url)
        with pytest.raises(ValidationError, match="frontend_url"):
            Config()


def test_config_requires_frontend_url_when_oauth_enabled():
    # model_construct skips settings sources, so the YAML test config does not interfere
    for frontend_url in (None, ""):
        unsafe_config = Config.model_construct(
            api=API.model_construct(frontend_url=frontend_url), auth=Auth(oauth=OAuth(enabled=True))
        )
        with pytest.raises(ValueError, match="api.frontend_url must be set"):
            unsafe_config.validate_oauth_frontend_url()

    Config.model_construct(
        api=API(frontend_url="https://clue.example"), auth=Auth(oauth=OAuth(enabled=True))
    ).validate_oauth_frontend_url()


def test_config_does_not_require_frontend_url_when_oauth_disabled():
    Config.model_construct(api=API(), auth=Auth(oauth=OAuth(enabled=False))).validate_oauth_frontend_url()
