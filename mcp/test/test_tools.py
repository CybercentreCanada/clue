from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from mcp.server.auth.provider import AccessToken

from clue_mcp import tools


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def tool(self, name):
        def register(function):
            self.tools[name] = function
            return function

        return register


@pytest.fixture
def registered_tools(monkeypatch):
    registry = ToolRegistry()
    api_client: Any = SimpleNamespace(call=AsyncMock(return_value={"outcome": "success"}))
    token = AccessToken(token="token", client_id="test", scopes=[])
    monkeypatch.setattr(tools, "get_access_token", lambda: token)
    tools.register_tools(registry, api_client)
    return registry.tools, api_client


async def test_execute_action_uses_execute_route_and_api_request_shape(registered_tools):
    registered, api_client = registered_tools

    result = await registered["execute_action"](
        plugin_id="example",
        action_id="block_ip",
        selector=tools.Selector(type="ip", value="1.2.3.4"),
        parameters={"duration": 60},
        max_timeout=10,
    )

    assert result == {"outcome": "success"}
    api_client.call.assert_awaited_once()
    assert api_client.call.await_args.kwargs["path"] == "actions/execute/example/block_ip"
    assert api_client.call.await_args.kwargs["body"] == {
        "duration": 60,
        "selector": {"type": "ip", "value": "1.2.3.4"},
    }
    assert api_client.call.await_args.kwargs["params"] == {"max_timeout": 10}


async def test_execute_action_rejects_reserved_parameter_override(registered_tools):
    registered, _ = registered_tools

    with pytest.raises(ValueError, match="reserved fields: selector"):
        await registered["execute_action"](
            plugin_id="example",
            action_id="block_ip",
            parameters={"selector": {}},
        )


async def test_enrich_encodes_value_and_serializes_options(registered_tools):
    registered, api_client = registered_tools

    await registered["enrich"](
        type_name="url",
        value="https://example.test/a?x=1",
        options=tools.EnrichmentOptions(sources=["vt", "-other"], include_raw=True),
    )

    assert api_client.call.await_args.kwargs["path"] == (
        "lookup/enrich/url/https%253A%252F%252Fexample.test%252Fa%253Fx%253D1/"
    )
    assert api_client.call.await_args.kwargs["params"] == {"sources": "vt|-other", "include_raw": True}


async def test_documentation_file_rejects_path_traversal(registered_tools):
    registered, api_client = registered_tools

    with pytest.raises(ValueError, match="without traversal segments"):
        await registered["serve_documentation_file"]("../secret.md")

    api_client.call.assert_not_awaited()
