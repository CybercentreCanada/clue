"""Tests covering error-response branches in CluePlugin endpoint methods.

Each test exercises one error branch that was not previously hit by the test suite,
ensuring consistent HTTP responses are returned rather than letting exceptions
propagate to Flask's default error handler.
"""

import logging
from unittest.mock import MagicMock

import pytest

from clue.common.exceptions import InvalidDataException
from clue.models.actions import Action, ActionResult, ExecuteRequest
from clue.models.fetchers import FetcherDefinition
from clue.models.network import QueryEntry
from clue.plugin import CluePlugin
from clue.plugin.models import BulkEntry


def _bad_token():
    """validate_token stub that always returns a validation error."""
    return None, "token invalid"


# ---------------------------------------------------------------------------
# Base plugin fixture (enrich-based, no cache)
# ---------------------------------------------------------------------------


@pytest.fixture
def plugin():
    return CluePlugin(
        app_name="test_endpoint_errors",
        classification="TLP:CLEAR",
        supported_types={"ipv4"},
        enrich=lambda *_: QueryEntry(count=1, annotations=[]),
        logger=logging.getLogger("test_endpoint_errors"),
        enable_cache=False,
    )


# ---------------------------------------------------------------------------
# lookup
# ---------------------------------------------------------------------------


class TestLookupErrors:
    def test_token_error_returns_401(self, plugin):
        plugin.validate_token = _bad_token
        response = plugin.app.test_client().get("/lookup/ipv4/1.2.3.4/")
        plugin.validate_token = None
        assert response.status_code == 401

    def test_enrich_exception_returns_error_response(self, plugin):
        plugin.enrich = MagicMock(side_effect=InvalidDataException("bad input"))
        response = plugin.app.test_client().get("/lookup/ipv4/1.2.3.4/")
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# bulk_lookup
# ---------------------------------------------------------------------------


class TestBulkLookupErrors:
    def test_token_error_returns_401(self, plugin):
        plugin.validate_token = _bad_token
        response = plugin.app.test_client().post("/lookup/", json=[{"type": "ipv4", "value": "1.2.3.4"}])
        plugin.validate_token = None
        assert response.status_code == 401

    def test_alternate_bulk_lookup_success(self):
        def alt_lookup(items, params, token):
            return {"ipv4": {item["value"]: BulkEntry(items=[QueryEntry(count=1, annotations=[])]) for item in items}}

        alt_plugin = CluePlugin(
            app_name="test_alt_lookup",
            classification="TLP:CLEAR",
            supported_types={"ipv4"},
            alternate_bulk_lookup=alt_lookup,
            logger=logging.getLogger("test_alt_lookup"),
            enable_cache=False,
        )
        response = alt_plugin.app.test_client().post("/lookup/", json=[{"type": "ipv4", "value": "1.2.3.4"}])
        assert response.status_code == 200
        data = response.get_json()
        assert data["api_response"]["ipv4"]["1.2.3.4"] is not None

    def test_alternate_bulk_lookup_raises_returns_error(self):
        alt_plugin = CluePlugin(
            app_name="test_alt_lookup_err",
            classification="TLP:CLEAR",
            supported_types={"ipv4"},
            alternate_bulk_lookup=MagicMock(side_effect=InvalidDataException("bad")),
            logger=logging.getLogger("test_alt_lookup_err"),
            enable_cache=False,
        )
        response = alt_plugin.app.test_client().post("/lookup/", json=[{"type": "ipv4", "value": "1.2.3.4"}])
        assert response.status_code == 400

    def test_alternate_bulk_lookup_non_dict_returns_500(self):
        alt_plugin = CluePlugin(
            app_name="test_alt_lookup_bad",
            classification="TLP:CLEAR",
            supported_types={"ipv4"},
            alternate_bulk_lookup=MagicMock(return_value=None),
            logger=logging.getLogger("test_alt_lookup_bad"),
            enable_cache=False,
        )
        response = alt_plugin.app.test_client().post("/lookup/", json=[{"type": "ipv4", "value": "1.2.3.4"}])
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# Action fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def plugin_with_action():
    return CluePlugin(
        app_name="test_action_errors",
        classification="TLP:CLEAR",
        supported_types={"ipv4"},
        enrich=lambda *_: QueryEntry(count=1, annotations=[]),
        run_action=MagicMock(
            return_value=ActionResult(outcome="success", summary="ok", format="markdown", output="markdown")
        ),
        get_action_status=MagicMock(
            return_value=ActionResult(outcome="success", summary="ok", format="markdown", output="markdown")
        ),
        actions=[
            Action[ExecuteRequest](
                id="test_action",
                name="Test Action",
                classification="TLP:CLEAR",
                supported_types={"ipv4"},
                accept_empty=True,
            )
        ],
        logger=logging.getLogger("test_action_errors"),
        enable_cache=False,
    )


# ---------------------------------------------------------------------------
# get_actions
# ---------------------------------------------------------------------------


class TestGetActionsErrors:
    def test_checked_actions_error_returns_500(self, plugin_with_action):
        plugin_with_action.setup_actions = MagicMock(side_effect=RuntimeError("crash"))
        response = plugin_with_action.app.test_client().get("/actions/")
        plugin_with_action.setup_actions = None
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# execute_action
# ---------------------------------------------------------------------------


class TestExecuteActionErrors:
    def test_checked_actions_error_returns_500(self, plugin_with_action):
        plugin_with_action.setup_actions = MagicMock(side_effect=RuntimeError("crash"))
        response = plugin_with_action.app.test_client().post("/actions/test_action/", json={})
        plugin_with_action.setup_actions = None
        assert response.status_code == 500

    def test_resolve_token_error_returns_401(self, plugin_with_action):
        # setup_actions is None so _get_actions returns plugin.actions without
        # calling validate_token; the second _resolve_token call in execute_action fails.
        plugin_with_action.validate_token = _bad_token
        response = plugin_with_action.app.test_client().post("/actions/test_action/", json={})
        plugin_with_action.validate_token = None
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# action_status
# ---------------------------------------------------------------------------


class TestActionStatusErrors:
    def test_checked_actions_error_returns_500(self, plugin_with_action):
        plugin_with_action.setup_actions = MagicMock(side_effect=RuntimeError("crash"))
        response = plugin_with_action.app.test_client().get("/actions/test_action/status/task-abc")
        plugin_with_action.setup_actions = None
        assert response.status_code == 500

    def test_resolve_token_error_returns_401(self, plugin_with_action):
        plugin_with_action.validate_token = _bad_token
        response = plugin_with_action.app.test_client().get("/actions/test_action/status/task-abc")
        plugin_with_action.validate_token = None
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Fetcher fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def plugin_with_fetcher():
    return CluePlugin(
        app_name="test_fetcher_errors",
        classification="TLP:CLEAR",
        supported_types={"ipv4"},
        enrich=lambda *_: QueryEntry(count=1, annotations=[]),
        run_fetcher=MagicMock(),
        get_fetcher_status=MagicMock(),
        fetchers=[
            FetcherDefinition(
                id="test_fetcher",
                classification="TLP:CLEAR",
                description="A test fetcher",
                format="json",
                supported_types={"ipv4"},
            )
        ],
        logger=logging.getLogger("test_fetcher_errors"),
        enable_cache=False,
    )


# ---------------------------------------------------------------------------
# execute_fetcher
# ---------------------------------------------------------------------------


class TestExecuteFetcherErrors:
    def test_resolve_token_error_returns_401(self, plugin_with_fetcher):
        plugin_with_fetcher.validate_token = _bad_token
        response = plugin_with_fetcher.app.test_client().post(
            "/fetchers/test_fetcher",
            json={"type": "ipv4", "value": "1.2.3.4"},
        )
        plugin_with_fetcher.validate_token = None
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# fetcher_status
# ---------------------------------------------------------------------------


class TestFetcherStatusErrors:
    def test_resolve_token_error_returns_401(self, plugin_with_fetcher):
        plugin_with_fetcher.validate_token = _bad_token
        response = plugin_with_fetcher.app.test_client().get("/fetchers/test_fetcher/status/task-abc")
        plugin_with_fetcher.validate_token = None
        assert response.status_code == 401
