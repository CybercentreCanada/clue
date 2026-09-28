from types import SimpleNamespace
from unittest.mock import patch

import pytest
from jwt.exceptions import InvalidTokenError, PyJWKClientError

from clue_mcp.auth import JSONWebTokenVerifier


@pytest.fixture()
def verifier() -> JSONWebTokenVerifier:
    return JSONWebTokenVerifier(
        issuer="https://issuer.example/realms/clue",
        jwks_uri="https://issuer.example/realms/clue/protocol/openid-connect/certs",
        audience="clue",
        required_scopes=["openid", "offline_access"],
        timeout=5.0,
    )


@pytest.mark.asyncio
async def test_verify_token_returns_none_on_jwks_client_error(verifier):
    with patch.object(
        verifier.jwks_client,
        "get_signing_key_from_jwt",
        side_effect=PyJWKClientError("network down"),
    ):
        result = await verifier.verify_token("raw-token")

    assert result is None


@pytest.mark.asyncio
async def test_verify_token_returns_none_on_invalid_token_error(verifier):
    with (
        patch.object(
            verifier.jwks_client,
            "get_signing_key_from_jwt",
            return_value=SimpleNamespace(key="fake-key"),
        ),
        patch(
            "clue_mcp.auth.jwt.decode",
            side_effect=InvalidTokenError("bad signature"),
        ),
    ):
        result = await verifier.verify_token("raw-token")

    assert result is None


@pytest.mark.asyncio
async def test_verify_token_rejects_audience_mismatch(verifier):
    claims = {
        "exp": 9999999999,
        "iat": 1111111111,
        "iss": "https://issuer.example/realms/clue",
        "aud": "other-audience",
        "scope": "offline_access",
        "azp": "cli-a",
    }

    with (
        patch.object(
            verifier.jwks_client,
            "get_signing_key_from_jwt",
            return_value=SimpleNamespace(key="fake-key"),
        ),
        patch("clue_mcp.auth.jwt.decode", return_value=claims),
    ):
        result = await verifier.verify_token("raw-token")

    assert result is None


@pytest.mark.asyncio
async def test_verify_token_rejects_missing_scope(verifier):
    claims = {
        "exp": 9999999999,
        "iat": 1111111111,
        "iss": "https://issuer.example/realms/clue",
        "aud": "clue",
        "scope": "different:scope",
        "azp": "cli-a",
    }

    with (
        patch.object(
            verifier.jwks_client,
            "get_signing_key_from_jwt",
            return_value=SimpleNamespace(key="fake-key"),
        ),
        patch("clue_mcp.auth.jwt.decode", return_value=claims),
    ):
        result = await verifier.verify_token("raw-token")

    assert result is None


@pytest.mark.asyncio
async def test_verify_token_accepts_valid_token(verifier):
    claims = {
        "exp": 9999999999,
        "iat": 1111111111,
        "iss": "https://issuer.example/realms/clue",
        "aud": ["clue", "other"],
        "scope": "openid profile offline_access",
        "azp": "cli-a",
    }

    with (
        patch.object(
            verifier.jwks_client,
            "get_signing_key_from_jwt",
            return_value=SimpleNamespace(key="fake-key"),
        ),
        patch("clue_mcp.auth.jwt.decode", return_value=claims),
    ):
        token = await verifier.verify_token("raw-token")

    assert token is not None
    assert token.token == "raw-token"
    assert token.client_id == "cli-a"
    assert token.resource == "clue"
    assert "offline_access" in token.scopes


@pytest.mark.asyncio
async def test_verify_token_accepts_all_required_scopes():
    verifier = JSONWebTokenVerifier(
        issuer="https://issuer.example/realms/clue",
        jwks_uri="https://issuer.example/realms/clue/protocol/openid-connect/certs",
        audience="clue",
        required_scopes=["openid", "offline_access"],
        timeout=5.0,
    )
    claims = {
        "exp": 9999999999,
        "iat": 1111111111,
        "iss": "https://issuer.example/realms/clue",
        "aud": "clue",
        "scope": "openid offline_access profile email",
        "azp": "clue",
    }

    with (
        patch.object(
            verifier.jwks_client,
            "get_signing_key_from_jwt",
            return_value=SimpleNamespace(key="fake-key"),
        ),
        patch("clue_mcp.auth.jwt.decode", return_value=claims),
    ):
        token = await verifier.verify_token("raw-token")

    assert token is not None
    assert token.scopes == ["openid", "offline_access", "profile", "email"]


@pytest.mark.asyncio
async def test_verify_token_rejects_non_integer_expiry(verifier):
    claims = {
        "exp": "not-a-timestamp",
        "iat": 1111111111,
        "iss": "https://issuer.example/realms/clue",
        "aud": "clue",
        "scope": "openid offline_access",
        "azp": "cli-a",
    }

    with (
        patch.object(
            verifier.jwks_client,
            "get_signing_key_from_jwt",
            return_value=SimpleNamespace(key="fake-key"),
        ),
        patch("clue_mcp.auth.jwt.decode", return_value=claims),
    ):
        token = await verifier.verify_token("raw-token")

    assert token is None


@pytest.mark.asyncio
async def test_verify_token_returns_none_on_unexpected_error(verifier):
    with patch.object(
        verifier.jwks_client,
        "get_signing_key_from_jwt",
        side_effect=RuntimeError("unexpected failure"),
    ):
        token = await verifier.verify_token("raw-token")

    assert token is None
