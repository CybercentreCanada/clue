import httpx
import pytest
from mcp.server.auth.provider import AccessToken

from clue_mcp.api import ClueApiClient
from clue_mcp.auth import AuthProvider


class AuthProviderStub(AuthProvider):
    async def get_clue_token(self, user_token: str) -> str:
        assert user_token == "user-token"
        return "clue-token"


TOKEN = AccessToken(token="user-token", client_id="test", scopes=[])


@pytest.mark.parametrize("payload", [["not", "an", "envelope"], {"unexpected": "shape"}])
async def test_call_rejects_invalid_response_envelope(payload):
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = ClueApiClient(
            base_url="https://clue.test/api/v1",
            auth_provider=AuthProviderStub(),
            client=http_client,
        )

        with pytest.raises(ValueError, match="expected format"):
            await client.call(TOKEN, "actions/", "GET")


async def test_call_sends_auth_query_and_json_body():
    def handle(request):
        assert request.url == "https://clue.test/api/v1/lookup/enrich?limit=2"
        assert request.headers["Authorization"] == "Bearer clue-token"
        assert request.read() == b'[{"type":"domain","value":"example.test"}]'
        return httpx.Response(200, json={"api_response": {"domain": {}}})

    transport = httpx.MockTransport(handle)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = ClueApiClient(
            base_url="https://clue.test/api/v1/",
            auth_provider=AuthProviderStub(),
            client=http_client,
        )

        result = await client.call(
            TOKEN,
            "/lookup/enrich",
            "POST",
            body=[{"type": "domain", "value": "example.test"}],
            params={"limit": 2},
        )

    assert result == {"domain": {}}


async def test_call_rejects_get_body_before_sending_request():
    transport = httpx.MockTransport(lambda request: pytest.fail("request should not be sent"))
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = ClueApiClient(
            base_url="https://clue.test/api/v1",
            auth_provider=AuthProviderStub(),
            client=http_client,
        )

        with pytest.raises(ValueError, match="not allowed"):
            await client.call(TOKEN, "lookup/types/", "GET", body={})
