from collections.abc import Callable
from unittest.mock import AsyncMock, Mock, patch

import pytest
from mcp.server.auth.provider import AccessToken

from clue_mcp.tools import REQUEST_TIMEOUT_BUFFER, EnrichmentOptions, Selector, register_tools

FAKE_TOKEN = AccessToken(token="fake-bearer", client_id="test-client", scopes=["clue"])
TOOL_NAMES = {
    "get_actions",
    "execute_action",
    "get_action_status",
    "get_fetchers",
    "run_fetcher",
    "get_fetcher_status",
    "get_types",
    "get_types_detection",
    "bulk_enrich",
    "enrich",
    "serve_documentation",
    "serve_documentation_file",
}


class _CaptureMCP:
    def __init__(self):
        self.tools: dict[str, Callable] = {}

    def tool(self, name: str):
        def decorator(tool):
            self.tools[name] = tool
            return tool

        return decorator


@pytest.fixture
def registered_tools():
    mcp = _CaptureMCP()
    api_client = Mock()
    api_client.call = AsyncMock(return_value={"status": "ok"})

    with patch("clue_mcp.tools.get_access_token", return_value=FAKE_TOKEN):
        register_tools(mcp, api_client)
        yield mcp.tools, api_client


def test_register_tools_registers_current_clue_surface(registered_tools):
    tools, _ = registered_tools

    assert set(tools) == TOOL_NAMES


async def test_tool_requires_authenticated_access_token():
    mcp = _CaptureMCP()
    api_client = Mock(call=AsyncMock())

    with patch("clue_mcp.tools.get_access_token", return_value=None):
        register_tools(mcp, api_client)

        with pytest.raises(ValueError, match="Access token is not available"):
            await mcp.tools["get_types"]()

    api_client.call.assert_not_awaited()


@pytest.mark.parametrize(
    ("tool_name", "expected_call"),
    [
        ("get_actions", {"path": "actions/", "method": "GET", "body": None}),
        ("get_fetchers", {"path": "fetchers/", "method": "GET", "body": None}),
        ("get_types", {"path": "lookup/types/", "method": "GET"}),
        ("get_types_detection", {"path": "lookup/types_detection/", "method": "GET"}),
    ],
)
async def test_listing_tools_forward_to_clue_api(registered_tools, tool_name, expected_call):
    tools, api_client = registered_tools

    result = await tools[tool_name]()

    assert result == {"status": "ok"}
    api_client.call.assert_awaited_once_with(user_access_token=FAKE_TOKEN, **expected_call)


async def test_execute_action_serializes_inputs_and_plugin_parameters(registered_tools):
    tools, api_client = registered_tools

    timeout: float = 12.5

    await tools["execute_action"](
        plugin_id="virustotal",
        action_id="submit",
        selectors=[Selector(type="sha256", value="abc")],
        context={"case": "123"},
        parameters={"priority": "high"},
        max_timeout=timeout,
    )

    api_client.call.assert_awaited_once_with(
        user_access_token=FAKE_TOKEN,
        path="actions/execute/virustotal/submit",
        method="POST",
        body={
            "priority": "high",
            "selectors": [{"type": "sha256", "value": "abc"}],
            "context": {"case": "123"},
        },
        params={"max_timeout": timeout},
        request_timeout=timeout + REQUEST_TIMEOUT_BUFFER,
    )


async def test_execute_action_rejects_ambiguous_plugin_parameters(registered_tools):
    tools, api_client = registered_tools

    with pytest.raises(ValueError, match="must not override reserved fields: selector"):
        await tools["execute_action"](
            plugin_id="plugin",
            action_id="action",
            parameters={"selector": {"type": "domain", "value": "example.ca"}},
        )

    api_client.call.assert_not_awaited()


async def test_action_status_encodes_identifiers_and_timeout(registered_tools):
    tools, api_client = registered_tools

    await tools["get_action_status"]("plugin name", "action+id", "task id", max_timeout=3)

    api_client.call.assert_awaited_once_with(
        user_access_token=FAKE_TOKEN,
        path="actions/plugin%20name/action%2Bid/status/task%20id",
        method="GET",
        body=None,
        params={"max_timeout": 3},
        request_timeout=3 + REQUEST_TIMEOUT_BUFFER,
    )


async def test_run_fetcher_serializes_selector(registered_tools):
    tools, api_client = registered_tools
    selector = Selector(type="domain", value="example.ca", classification="TLP:CLEAR")

    await tools["run_fetcher"]("plugin", "fetcher", selector)

    api_client.call.assert_awaited_once_with(
        user_access_token=FAKE_TOKEN,
        path="fetchers/plugin/fetcher",
        method="POST",
        body={"type": "domain", "value": "example.ca", "classification": "TLP:CLEAR"},
        params=None,
        request_timeout=None,
    )


async def test_fetcher_status_forwards_task_and_timeout(registered_tools):
    tools, api_client = registered_tools

    await tools["get_fetcher_status"]("plugin", "fetcher", "task", max_timeout=4)

    api_client.call.assert_awaited_once_with(
        user_access_token=FAKE_TOKEN,
        path="fetchers/plugin/fetcher/status/task",
        method="GET",
        params={"max_timeout": 4},
        request_timeout=6,
    )


async def test_bulk_enrich_serializes_data_and_options(registered_tools):
    tools, api_client = registered_tools

    await tools["bulk_enrich"](
        [Selector(type="ipv4", value="192.0.2.1")],
        EnrichmentOptions(sources=["source-a", "-source-b"], limit=5, no_cache=True, max_timeout=8),
    )

    api_client.call.assert_awaited_once_with(
        user_access_token=FAKE_TOKEN,
        path="lookup/enrich",
        method="POST",
        body=[{"type": "ipv4", "value": "192.0.2.1"}],
        params={"sources": "source-a|-source-b", "max_timeout": 8.0, "limit": 5, "no_cache": True},
        request_timeout=10.0,
    )


async def test_enrich_applies_clue_double_encoding(registered_tools):
    tools, api_client = registered_tools

    await tools["enrich"]("domain", "example.ca/path value")

    api_client.call.assert_awaited_once_with(
        user_access_token=FAKE_TOKEN,
        path="lookup/enrich/domain/example.ca%252Fpath%2520value/",
        method="GET",
        params=None,
        request_timeout=None,
    )


async def test_documentation_tools_forward_filter_and_safe_nested_path(registered_tools):
    tools, api_client = registered_tools

    await tools["serve_documentation"]("deployment")
    await tools["serve_documentation_file"]("admin/setup guide.md")

    assert api_client.call.await_args_list[0].kwargs == {
        "user_access_token": FAKE_TOKEN,
        "path": "static/docs",
        "method": "GET",
        "params": {"filter": "deployment"},
    }
    assert api_client.call.await_args_list[1].kwargs == {
        "user_access_token": FAKE_TOKEN,
        "path": "static/docs/admin/setup%20guide.md",
        "method": "GET",
    }


@pytest.mark.parametrize("filename", ["", "/absolute.md", "../secret.md", "folder/../secret.md", r"folder\file.md"])
async def test_documentation_file_rejects_paths_llm_should_not_send(registered_tools, filename):
    tools, api_client = registered_tools

    with pytest.raises(ValueError, match="relative path"):
        await tools["serve_documentation_file"](filename)

    api_client.call.assert_not_awaited()


@pytest.mark.parametrize("identifier", ["", ".", "..", "plugin/action", r"plugin\action", "plugin\nname"])
async def test_route_identifiers_reject_invalid_segments(registered_tools, identifier):
    tools, api_client = registered_tools

    with pytest.raises(ValueError, match="plugin_id must be a non-empty route segment"):
        await tools["run_fetcher"](identifier, "fetcher", Selector(type="domain", value="example.ca"))

    api_client.call.assert_not_awaited()
