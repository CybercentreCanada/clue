"""Integration tests for clue.plugin.helpers.central_server.

These tests exercise the cross-plugin communication helpers against the live
central API and the test plugin server, verifying that a plugin can:

  - discover which sources and types are available  (get_sources)
  - run bulk enrichment through the central API     (enrich)
  - list and execute actions                        (list_actions / execute_action)
  - list and run fetchers                           (list_fetchers / run_fetcher)

The helpers require an active Flask request context because they read auth
headers from `flask.request`.  We use the test plugin's own Flask app to
provide that context, injecting a real Keycloak-issued token so the central
API honours the request.
"""

import pytest

from clue.models.actions import ActionResult
from clue.models.fetchers import FetcherResult
from clue.models.selector import Selector
from clue.plugin.helpers.central_server import (
    enrich,
    execute_action,
    get_sources,
    list_actions,
    list_fetchers,
    run_fetcher,
)
from clue.plugin.models import BulkEntry
from test.utils.oauth_credentials import get_token
from test.utils.test_server import plugin as test_plugin


@pytest.fixture(scope="module")
def access_token():
    token = get_token()
    if not token:
        pytest.skip("Could not obtain a Keycloak token — Keycloak may not be running.")
    return token


@pytest.fixture(scope="module")
def central_url(host):
    """Override the central server URL so helpers point at the live test instance."""
    import clue.plugin.helpers.central_server as cs

    original = cs.CENTRAL_SERVER_URL
    cs.CENTRAL_SERVER_URL = host
    yield host
    cs.CENTRAL_SERVER_URL = original


# ---------------------------------------------------------------------------
# get_sources
# ---------------------------------------------------------------------------


def test_get_sources_returns_test_plugin(access_token, central_url):
    """get_sources() should include the 'test' plugin with its supported types."""
    with test_plugin.app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
        sources = get_sources()

    assert isinstance(sources, dict)
    assert "test" in sources, f"'test' not found in sources: {list(sources.keys())}"
    assert set(sources["test"]) >= {"ipv4", "ipv6", "port", "sha256"}


def test_get_sources_returns_dict_on_unauthenticated(central_url):
    """get_sources() returns an empty dict (not an exception) when unauthenticated."""
    with test_plugin.app.test_request_context():
        result = get_sources()

    # Central API will return 401; helper should swallow it and return {}
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# enrich
# ---------------------------------------------------------------------------


def test_enrich_single_selector(access_token, central_url):
    """enrich() on a single selector returns a correctly shaped BulkEntry."""
    selector = Selector(type="ipv4", value="127.0.0.1")

    with test_plugin.app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
        result = enrich("test", selector, timeout=5.0)

    assert "ipv4" in result, f"Expected 'ipv4' key in result: {list(result.keys())}"
    assert "127.0.0.1" in result["ipv4"]
    entry = result["ipv4"]["127.0.0.1"]["test"]
    assert isinstance(entry, BulkEntry)
    assert entry.error is None
    assert len(entry.items) > 0
    assert entry.items[0].count == 10


def test_enrich_bulk_selectors(access_token, central_url):
    """enrich() on multiple selectors returns results for each one."""
    selectors = [
        Selector(type="ipv4", value="127.0.0.1"),
        Selector(type="ipv6", value="127.0.0.2"),
    ]

    with test_plugin.app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
        result = enrich("test", selectors, timeout=5.0)

    assert "ipv4" in result
    assert "ipv6" in result
    assert result["ipv4"]["127.0.0.1"]["test"].error is None
    assert result["ipv6"]["127.0.0.2"]["test"].error is None


def test_enrich_multiple_sources(access_token, central_url):
    """enrich() propagates sources filter; 'bad' source should return an error entry."""
    selector = Selector(type="ipv4", value="127.0.0.1")

    with test_plugin.app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
        result = enrich(["test", "bad"], selector, timeout=5.0)

    assert result["ipv4"]["127.0.0.1"]["test"].error is None
    assert result["ipv4"]["127.0.0.1"]["bad"].error is not None


def test_enrich_empty_sources_queries_all(access_token, central_url):
    """enrich() with an empty sources list queries all available sources."""
    selector = Selector(type="ipv4", value="127.0.0.1")

    with test_plugin.app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
        result = enrich([], selector, timeout=5.0)

    # At minimum the 'test' plugin should respond
    assert "test" in result.get("ipv4", {}).get("127.0.0.1", {})


def test_enrich_ip_type_normalisation(access_token, central_url):
    """Selector(type='ip') is normalised to ipv4/ipv6 before enrichment."""
    selector_v4 = Selector(type="ip", value="127.0.0.1")
    selector_v6 = Selector(type="ip", value="2001:db8::1")

    with test_plugin.app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
        result = enrich("test", [selector_v4, selector_v6], timeout=5.0)

    assert "ipv4" in result
    assert "ipv6" in result


def test_enrich_annotations_shape(access_token, central_url):
    """Items in a BulkEntry from the test plugin contain the expected annotation."""
    selector = Selector(type="ipv4", value="127.0.0.1")

    with test_plugin.app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
        result = enrich("test", selector, timeout=5.0)

    item = result["ipv4"]["127.0.0.1"]["test"].items[0]
    annotation = item.annotations[0]
    assert annotation.type == "opinion"
    assert annotation.value == "malicious"
    assert annotation.confidence == pytest.approx(0.7)
    assert annotation.analytic == "test enrichment"


def test_enrich_no_cache_param(access_token, central_url):
    """enrich() with no_cache=True still returns valid results."""
    selector = Selector(type="ipv4", value="127.0.0.1")

    with test_plugin.app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
        result = enrich("test", selector, timeout=5.0, no_cache=True)

    assert result["ipv4"]["127.0.0.1"]["test"].error is None


# ---------------------------------------------------------------------------
# list_actions / execute_action
# ---------------------------------------------------------------------------


def test_list_actions_includes_test_plugin(access_token, central_url):
    """list_actions() exposes test plugin actions keyed as 'test.<action_id>'."""
    with test_plugin.app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
        actions = list_actions()

    assert isinstance(actions, dict)
    assert "test.test_action" in actions, f"Keys: {list(actions.keys())}"
    spec = actions["test.test_action"]
    assert spec.name == "Test Action"
    assert spec.classification == "TLP:CLEAR"
    assert "ipv4" in spec.supported_types or "ip" in spec.supported_types


def test_execute_action_success(access_token, central_url):
    """execute_action() returns a successful ActionResult from test.test_action."""
    payload = {
        "selector": {"type": "ip", "value": "127.0.0.1"},
        "other_choice": "b",
    }

    with test_plugin.app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
        result = execute_action("test", "test_action", payload, timeout=5.0)

    assert isinstance(result, ActionResult)
    assert result.outcome == "success"
    assert result.summary == "We got a value"
    assert result.output["value"]["value"] == "127.0.0.1"


def test_execute_action_with_param(access_token, central_url):
    """execute_action() passes extra action parameters correctly."""
    payload = {
        "selector": {"type": "ip", "value": "127.0.0.1"},
        "other_value": "cross-plugin-test",
        "other_choice": "b",
    }

    with test_plugin.app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
        result = execute_action("test", "test_action", payload, timeout=5.0)

    assert result.outcome == "success"
    assert result.summary == "We got a param value"
    assert result.output["value"] == "cross-plugin-test"


def test_execute_action_pivot(access_token, central_url):
    """execute_action() handles pivot-format actions that return a URL."""
    payload = {"selector": {"type": "ip", "value": "127.0.0.1"}}

    with test_plugin.app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
        result = execute_action("test", "test_pivot", payload, timeout=5.0)

    assert result.outcome == "success"
    assert result.format == "pivot"
    assert "127.0.0.1" in str(result.output)


def test_execute_action_unknown_plugin(access_token, central_url):
    """execute_action() returns a failure result for an unknown plugin."""
    with test_plugin.app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
        result = execute_action("no_such_plugin", "some_action", timeout=5.0)

    assert result.outcome == "failure"


# ---------------------------------------------------------------------------
# list_fetchers / run_fetcher
# ---------------------------------------------------------------------------


def test_list_fetchers_includes_test_plugin(access_token, central_url):
    """list_fetchers() exposes test plugin fetchers keyed as 'test.<fetcher_id>'."""
    with test_plugin.app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
        fetchers = list_fetchers()

    assert isinstance(fetchers, dict)
    assert "test.json" in fetchers, f"Keys: {list(fetchers.keys())}"
    assert fetchers["test.json"].format == "json"
    assert fetchers["test.json"].description == "test fetcher json"

    assert "test.image" in fetchers
    assert "test.graph" in fetchers


def test_run_fetcher_json(access_token, central_url):
    """run_fetcher() on the test plugin json fetcher returns expected data."""
    selector = Selector(type="ipv4", value="127.0.0.1")

    with test_plugin.app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
        result = run_fetcher("test", "json", selector, timeout=5.0)

    assert isinstance(result, FetcherResult)
    assert result.outcome == "success"
    assert result.data == {"potato": "test"}


def test_run_fetcher_image(access_token, central_url):
    """run_fetcher() on the image fetcher returns a non-null image data field."""
    selector = Selector(type="ipv4", value="127.0.0.1")

    with test_plugin.app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
        result = run_fetcher("test", "image", selector, timeout=5.0)

    assert result.outcome == "success"
    assert result.data is not None


def test_run_fetcher_unknown_plugin(access_token, central_url):
    """run_fetcher() returns a failure result for an unknown plugin."""
    selector = Selector(type="ipv4", value="127.0.0.1")

    with test_plugin.app.test_request_context(headers={"Authorization": f"Bearer {access_token}"}):
        result = run_fetcher("no_such_plugin", "json", selector, timeout=5.0)

    assert result.outcome == "failure"
    assert result.error is not None
