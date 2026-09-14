import json
import os
from urllib.parse import urlparse, urlunparse

import httpx
import pytest

from clue_mcp.config import AUTH, CLUE_API, MCPSettings

RUN_MCP_NETWORK_TESTS = os.environ.get("RUN_MCP_NETWORK_TESTS", "").lower() in {
    "1",
    "true",
    "yes",
}

pytestmark = pytest.mark.skipif(
    not RUN_MCP_NETWORK_TESTS,
    reason=("Live MCP network tests are disabled by default. Set RUN_MCP_NETWORK_TESTS=1 to enable."),
)

TEST_USERNAME = os.environ.get("TEST_AUTH_USERNAME")
TEST_PASSWORD = os.environ.get("TEST_AUTH_PASSWORD")
TEST_SCOPE = os.environ.get("TEST_AUTH_SCOPE", MCPSettings.SCOPE)

if RUN_MCP_NETWORK_TESTS:
    missing_vars = [
        name
        for name, value in {
            "TEST_AUTH_USERNAME": TEST_USERNAME,
            "TEST_AUTH_PASSWORD": TEST_PASSWORD,
        }.items()
        if not value
    ]
    if missing_vars:
        pytest.skip(
            "Missing required environment variables for live MCP network tests: " + ", ".join(missing_vars),
            allow_module_level=True,
        )


def _mcp_request_url() -> str:
    base_url = MCPSettings.BASE_URL
    parsed = urlparse(base_url)

    if parsed.hostname not in {"0.0.0.0", "::"}:
        return base_url

    netloc = "localhost"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"

    return urlunparse(parsed._replace(netloc=netloc))


def get_token() -> str:
    payload = {
        "grant_type": "password",
        "audience": MCPSettings.AUDIENCE,
        "client_id": AUTH.CLIENT_ID,
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
        "scope": TEST_SCOPE,
    }
    if AUTH.CLIENT_SECRET:
        payload["client_secret"] = AUTH.CLIENT_SECRET

    response = httpx.post(AUTH.TOKEN_URL, data=payload, timeout=CLUE_API.TIMEOUT)
    response.raise_for_status()
    token = response.json().get("access_token")
    assert token, "Token response did not include access_token"
    return token


def _initialize_response_messages(response: httpx.Response) -> list[dict]:
    """Extract JSON-RPC responses from either JSON or streamable-HTTP SSE output."""
    content_type = response.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        payload = response.json()
        messages = payload if isinstance(payload, list) else [payload]
    elif "text/event-stream" in content_type:
        messages = [
            json.loads(line.removeprefix("data:").strip())
            for line in response.text.splitlines()
            if line.startswith("data:") and line.removeprefix("data:").strip()
        ]
    else:
        pytest.fail(f"Unexpected MCP response content type: {content_type or 'missing'}")

    assert all(isinstance(message, dict) for message in messages), "MCP response was not a JSON-RPC object"
    return messages


def test_mcp_server_connection():
    token = get_token()
    url_mcp = _mcp_request_url()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    payload = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pytest-connection-checker", "version": "1.0.0"},
        },
        "id": 1,
    }

    response = httpx.post(url_mcp, headers=headers, json=payload, timeout=CLUE_API.TIMEOUT)
    assert response.status_code == 200
    responses = _initialize_response_messages(response)
    matching_responses = [response for response in responses if str(response.get("id")) == "1"]
    assert matching_responses, "MCP initialize response did not include request ID 1"
    initialize_response = matching_responses[-1]
    assert "error" not in initialize_response, f"MCP initialization failed: {initialize_response['error']}"
    assert "result" in initialize_response, "MCP initialize response did not include a result"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
