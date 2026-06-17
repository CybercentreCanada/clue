import logging
from unittest.mock import MagicMock, patch

import pytest
import requests

from clue.models.actions import ActionResult, ActionSpec
from clue.models.fetchers import FetcherDefinition, FetcherResult
from clue.models.network import QueryEntry
from clue.models.selector import Selector
from clue.plugin import CluePlugin
from clue.plugin.helpers.central_server import (
    _SESSIONS,
    _connect_to_central_server,
    enrich,
    execute_action,
    get_sources,
    list_actions,
    list_fetchers,
    run_fetcher,
)
from clue.plugin.models import BulkEntry


@pytest.fixture(scope="module")
def mock_plugin():
    plugin = CluePlugin(
        app_name="tester",
        supported_types={"ipv4", "ipv6"},
        enrich=lambda *args: QueryEntry(count=10, annotations=[], link="https://example.com"),
        logger=logging.getLogger("test"),
        classification="TLP:CLEAR",
    )
    return plugin


# ---------------------------------------------------------------------------
# _connect_to_central_server – token extraction & header building
# ---------------------------------------------------------------------------


def test_connect_uses_xclue_token_as_primary(mock_plugin: CluePlugin, caplog):
    """X-Clue-Authorization is used as the primary bearer and the raw Authorization
    is forwarded as X-Clue-Authorization."""
    with (
        mock_plugin.app.test_request_context(
            headers={
                "X-Clue-Authorization": "pre-obo-token",
                "Authorization": "Bearer raw-token",
            }
        ),
        caplog.at_level(logging.INFO),
    ):
        _session, headers = _connect_to_central_server()

    assert headers["Authorization"] == "Bearer pre-obo-token"
    assert headers["X-Clue-Authorization"] == "raw-token"
    assert "using pre-OBO token" in caplog.text


def test_connect_falls_back_to_auth_header(mock_plugin: CluePlugin, caplog):
    """Falls back to Authorization when X-Clue-Authorization is absent."""
    with (
        mock_plugin.app.test_request_context(headers={"Authorization": "Bearer raw-token"}),
        caplog.at_level(logging.WARNING),
    ):
        _session, headers = _connect_to_central_server()

    assert headers["Authorization"] == "Bearer raw-token"
    assert "X-Clue-Authorization" not in headers
    assert "X-Clue-Authorization header not specified" in caplog.text


def test_connect_no_token(mock_plugin: CluePlugin, caplog):
    """No auth headers results in an unauthenticated headers dict."""
    with (
        mock_plugin.app.test_request_context(),
        caplog.at_level(logging.WARNING),
    ):
        _session, headers = _connect_to_central_server()

    assert "Authorization" not in headers
    assert "No token specified" in caplog.text


def test_connect_timeout_variation_does_not_grow_session_cache(mock_plugin: CluePlugin):
    """Per-call timeout changes should not create additional cached Sessions."""
    _SESSIONS.clear()

    with mock_plugin.app.test_request_context(headers={"Authorization": "Bearer raw-token"}):
        session_1, _ = _connect_to_central_server()
        # Timeout values are used per request, not for session cache partitioning.
        session_2, _ = _connect_to_central_server()

    assert len(_SESSIONS) == 1
    assert session_1 is session_2


# ---------------------------------------------------------------------------
# get_sources
# ---------------------------------------------------------------------------


def test_get_sources_success(mock_plugin: CluePlugin):
    response_data = {"api_response": {"geoip": ["ipv4", "ipv6"], "vt": ["domain"]}}
    mock_rsp = MagicMock()
    mock_rsp.json.return_value = response_data
    mock_rsp.raise_for_status.return_value = None

    with (
        mock_plugin.app.test_request_context(headers={"Authorization": "Bearer tok"}),
        patch("clue.plugin.helpers.central_server._get_session") as mock_sess_factory,
    ):
        mock_sess_factory.return_value.get.return_value = mock_rsp
        result = get_sources()

    assert result == {"geoip": ["ipv4", "ipv6"], "vt": ["domain"]}


def test_get_sources_connection_error(mock_plugin: CluePlugin):
    with (
        mock_plugin.app.test_request_context(headers={"Authorization": "Bearer tok"}),
        patch("clue.plugin.helpers.central_server._get_session") as mock_sess_factory,
    ):
        mock_sess_factory.return_value.get.side_effect = requests.exceptions.ConnectionError
        result = get_sources()

    assert result == {}


# ---------------------------------------------------------------------------
# enrich
# ---------------------------------------------------------------------------


def _make_enrich_response(source: str = "geoip") -> dict:
    return {
        "api_response": {
            "ipv4": {
                "1.2.3.4": {
                    source: {
                        "type": "ipv4",
                        "value": "1.2.3.4",
                        "source": source,
                        "error": None,
                        "items": [{"count": 1, "annotations": [], "classification": "TLP:CLEAR"}],
                        "raw_data": None,
                    }
                }
            }
        }
    }


def test_enrich_single_selector_and_source(mock_plugin: CluePlugin):
    selector = Selector(type="ipv4", value="1.2.3.4")
    mock_rsp = MagicMock()
    mock_rsp.json.return_value = _make_enrich_response("geoip")
    mock_rsp.raise_for_status.return_value = None

    with (
        mock_plugin.app.test_request_context(headers={"Authorization": "Bearer tok"}),
        patch("clue.plugin.helpers.central_server._get_session") as mock_sess_factory,
    ):
        mock_sess_factory.return_value.post.return_value = mock_rsp
        result = enrich("geoip", selector)

    assert "ipv4" in result
    assert "1.2.3.4" in result["ipv4"]
    assert "geoip" in result["ipv4"]["1.2.3.4"]
    entry = result["ipv4"]["1.2.3.4"]["geoip"]
    assert isinstance(entry, BulkEntry)
    assert entry.error is None
    assert len(entry.items) == 1


def test_enrich_multi_source_and_selector(mock_plugin: CluePlugin):
    selectors = [Selector(type="ipv4", value="1.2.3.4"), Selector(type="ipv4", value="5.6.7.8")]
    response = {
        "api_response": {
            "ipv4": {
                "1.2.3.4": {"geoip": {"error": None, "items": [], "raw_data": None}},
                "5.6.7.8": {"geoip": {"error": "not found", "items": [], "raw_data": None}},
            }
        }
    }
    mock_rsp = MagicMock()
    mock_rsp.json.return_value = response
    mock_rsp.raise_for_status.return_value = None

    with (
        mock_plugin.app.test_request_context(headers={"Authorization": "Bearer tok"}),
        patch("clue.plugin.helpers.central_server._get_session") as mock_sess_factory,
    ):
        mock_sess_factory.return_value.post.return_value = mock_rsp
        result = enrich(["geoip"], selectors)

    assert result["ipv4"]["5.6.7.8"]["geoip"].error == "not found"


def test_enrich_connection_error(mock_plugin: CluePlugin):
    with (
        mock_plugin.app.test_request_context(headers={"Authorization": "Bearer tok"}),
        patch("clue.plugin.helpers.central_server._get_session") as mock_sess_factory,
    ):
        mock_sess_factory.return_value.post.side_effect = requests.exceptions.ConnectionError
        result = enrich("geoip", Selector(type="ipv4", value="1.2.3.4"))

    assert result == {}


# ---------------------------------------------------------------------------
# list_actions / execute_action
# ---------------------------------------------------------------------------

_ACTION_SPEC_DATA = {
    "geoip.locate": {
        "id": "locate",
        "name": "Locate IP",
        "classification": "TLP:CLEAR",
        "supported_types": ["ipv4"],
        "params": {"$defs": {}, "type": "object", "properties": {}},
    }
}


def test_list_actions_success(mock_plugin: CluePlugin):
    mock_rsp = MagicMock()
    mock_rsp.json.return_value = {"api_response": _ACTION_SPEC_DATA}
    mock_rsp.raise_for_status.return_value = None

    with (
        mock_plugin.app.test_request_context(headers={"Authorization": "Bearer tok"}),
        patch("clue.plugin.helpers.central_server._get_session") as mock_sess_factory,
    ):
        mock_sess_factory.return_value.get.return_value = mock_rsp
        result = list_actions()

    assert "geoip.locate" in result
    assert isinstance(result["geoip.locate"], ActionSpec)


def test_execute_action_success(mock_plugin: CluePlugin):
    mock_rsp = MagicMock()
    mock_rsp.json.return_value = {
        "api_response": {"outcome": "success", "format": "markdown", "output": "Location: Canada", "summary": "Done"}
    }
    mock_rsp.raise_for_status.return_value = None

    with (
        mock_plugin.app.test_request_context(headers={"Authorization": "Bearer tok"}),
        patch("clue.plugin.helpers.central_server._get_session") as mock_sess_factory,
    ):
        mock_sess_factory.return_value.post.return_value = mock_rsp
        result = execute_action("geoip", "locate", {"selector": {"type": "ipv4", "value": "1.2.3.4"}})

    assert isinstance(result, ActionResult)
    assert result.outcome == "success"
    assert result.summary == "Done"


def test_execute_action_connection_error(mock_plugin: CluePlugin):
    with (
        mock_plugin.app.test_request_context(headers={"Authorization": "Bearer tok"}),
        patch("clue.plugin.helpers.central_server._get_session") as mock_sess_factory,
    ):
        mock_sess_factory.return_value.post.side_effect = requests.exceptions.ConnectionError
        result = execute_action("geoip", "locate")

    assert result.outcome == "failure"
    assert "geoip.locate" in (result.summary or "")


# ---------------------------------------------------------------------------
# list_fetchers / run_fetcher
# ---------------------------------------------------------------------------

_FETCHER_DEF_DATA = {
    "geoip.location_report": {
        "id": "location_report",
        "classification": "TLP:CLEAR",
        "description": "Returns a location report",
        "format": "json",
        "supported_types": ["ipv4"],
    }
}


def test_list_fetchers_success(mock_plugin: CluePlugin):
    mock_rsp = MagicMock()
    mock_rsp.json.return_value = {"api_response": _FETCHER_DEF_DATA}
    mock_rsp.raise_for_status.return_value = None

    with (
        mock_plugin.app.test_request_context(headers={"Authorization": "Bearer tok"}),
        patch("clue.plugin.helpers.central_server._get_session") as mock_sess_factory,
    ):
        mock_sess_factory.return_value.get.return_value = mock_rsp
        result = list_fetchers()

    assert "geoip.location_report" in result
    assert isinstance(result["geoip.location_report"], FetcherDefinition)


def test_run_fetcher_success(mock_plugin: CluePlugin):
    mock_rsp = MagicMock()
    mock_rsp.json.return_value = {"api_response": {"outcome": "success", "data": "<html/>", "format": "html"}}
    mock_rsp.raise_for_status.return_value = None

    with (
        mock_plugin.app.test_request_context(headers={"Authorization": "Bearer tok"}),
        patch("clue.plugin.helpers.central_server._get_session") as mock_sess_factory,
    ):
        mock_sess_factory.return_value.post.return_value = mock_rsp
        result = run_fetcher("geoip", "location_report", Selector(type="ipv4", value="1.2.3.4"))

    assert isinstance(result, FetcherResult)
    assert result.outcome == "success"


def test_run_fetcher_connection_error(mock_plugin: CluePlugin):
    with (
        mock_plugin.app.test_request_context(headers={"Authorization": "Bearer tok"}),
        patch("clue.plugin.helpers.central_server._get_session") as mock_sess_factory,
    ):
        mock_sess_factory.return_value.post.side_effect = requests.exceptions.ConnectionError
        result = run_fetcher("geoip", "location_report", Selector(type="ipv4", value="1.2.3.4"))

    assert result.outcome == "failure"
    assert "geoip.location_report" in (result.error or "")
