"""Unit tests for CluePlugin private helper methods.

Covers the three helpers introduced to reduce repeated exception-handling boilerplate:
  - _resolve_token
  - _call_plugin_func
  - _get_checked_actions
"""

import logging
from unittest.mock import MagicMock

import pytest

from clue.common.exceptions import (
    InvalidDataException,
    NotFoundException,
    TimeoutException,
    UnprocessableException,
)
from clue.models.network import QueryEntry
from clue.plugin import CluePlugin


@pytest.fixture
def plugin():
    """Minimal CluePlugin instance for testing internal helpers."""
    return CluePlugin(
        app_name="test_helpers",
        classification="TLP:CLEAR",
        supported_types={"ipv4"},
        enrich=lambda *_: QueryEntry(count=1, annotations=[]),
        logger=logging.getLogger("test_helpers"),
        enable_cache=False,
    )


# ---------------------------------------------------------------------------
# _resolve_token
# ---------------------------------------------------------------------------


class TestResolveToken:
    def test_no_validator_returns_none_and_no_error(self, plugin):
        with plugin.app.test_request_context():
            token, error_response = plugin._resolve_token()

        assert token is None
        assert error_response is None

    def test_no_validator_without_context_logs_generic_warning(self, plugin, caplog):
        with caplog.at_level(logging.WARNING):
            with plugin.app.test_request_context():
                plugin._resolve_token()

        assert any("token" in r.message.lower() for r in caplog.records)

    def test_no_validator_with_context_includes_context_in_warning(self, plugin, caplog):
        with caplog.at_level(logging.WARNING):
            with plugin.app.test_request_context():
                plugin._resolve_token(context="action")

        assert any("action" in r.message for r in caplog.records)

    def test_valid_token_returned(self, plugin):
        plugin.validate_token = lambda: ("my-token", None)

        with plugin.app.test_request_context():
            token, error_response = plugin._resolve_token()

        assert token == "my-token"
        assert error_response is None

    def test_validation_error_returns_401_response(self, plugin):
        plugin.validate_token = lambda: (None, "invalid token")

        with plugin.app.test_request_context():
            token, error_response = plugin._resolve_token()

        assert token is None
        assert error_response is not None
        assert error_response.status_code == 401

    def test_validation_error_message_included_in_response(self, plugin):
        plugin.validate_token = lambda: (None, "token expired")

        with plugin.app.test_request_context():
            _, error_response = plugin._resolve_token()

        data = error_response.get_json()
        assert "token expired" in data["api_error_message"]

    def test_validator_raises_returns_500_response(self, plugin):
        plugin.validate_token = MagicMock(side_effect=RuntimeError("catastrophic"))

        with plugin.app.test_request_context():
            token, error_response = plugin._resolve_token()

        assert token is None
        assert error_response is not None
        assert error_response.status_code == 500

    def test_validator_raises_logs_exception(self, plugin, caplog):
        plugin.validate_token = MagicMock(side_effect=RuntimeError("catastrophic"))

        with caplog.at_level(logging.ERROR):
            with plugin.app.test_request_context():
                plugin._resolve_token()

        assert any("validate_token" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# _call_plugin_func
# ---------------------------------------------------------------------------


class TestCallPluginFunc:
    def test_success_returns_result_and_no_error(self, plugin):
        func = MagicMock(return_value="the-result")

        with plugin.app.test_request_context():
            result, error_response = plugin._call_plugin_func(func)

        assert result == "the-result"
        assert error_response is None

    def test_args_and_kwargs_forwarded_to_func(self, plugin):
        func = MagicMock(return_value=42)

        with plugin.app.test_request_context():
            result, _ = plugin._call_plugin_func(func, "a", "b", key="val")

        func.assert_called_once_with("a", "b", key="val")
        assert result == 42

    def test_invalid_data_exception_returns_400(self, plugin):
        func = MagicMock(side_effect=InvalidDataException("bad input"))

        with plugin.app.test_request_context():
            result, error_response = plugin._call_plugin_func(func)

        assert result is None
        assert error_response.status_code == 400
        assert "bad input" in error_response.get_json()["api_error_message"]

    def test_not_found_exception_returns_404(self, plugin):
        func = MagicMock(side_effect=NotFoundException())

        with plugin.app.test_request_context():
            result, error_response = plugin._call_plugin_func(func)

        assert result is None
        assert error_response.status_code == 404

    def test_timeout_exception_returns_408(self, plugin):
        func = MagicMock(side_effect=TimeoutException("timed out"))

        with plugin.app.test_request_context():
            result, error_response = plugin._call_plugin_func(func)

        assert result is None
        assert error_response.status_code == 408

    def test_timeout_exception_falls_back_to_default_message(self, plugin):
        func = MagicMock(side_effect=TimeoutException(""))

        with plugin.app.test_request_context():
            _, error_response = plugin._call_plugin_func(func)

        assert "Request timed out" in error_response.get_json()["api_error_message"]

    def test_unprocessable_exception_returns_422(self, plugin):
        func = MagicMock(side_effect=UnprocessableException("malformed"))

        with plugin.app.test_request_context():
            result, error_response = plugin._call_plugin_func(func)

        assert result is None
        assert error_response.status_code == 422
        assert "malformed" in error_response.get_json()["api_error_message"]

    def test_unexpected_exception_returns_500(self, plugin):
        func = MagicMock(side_effect=RuntimeError("boom"))

        with plugin.app.test_request_context():
            result, error_response = plugin._call_plugin_func(func)

        assert result is None
        assert error_response.status_code == 500

    def test_unexpected_exception_logs_error(self, plugin, caplog):
        func = MagicMock(side_effect=RuntimeError("boom"))

        with caplog.at_level(logging.ERROR):
            with plugin.app.test_request_context():
                plugin._call_plugin_func(func)

        assert any(r.levelno >= logging.ERROR for r in caplog.records)


# ---------------------------------------------------------------------------
# _get_checked_actions
# ---------------------------------------------------------------------------


class TestGetCheckedActions:
    def test_no_setup_actions_returns_empty_list_and_no_error(self, plugin):
        with plugin.app.test_request_context():
            actions, error_response = plugin._get_checked_actions()

        assert actions == []
        assert error_response is None

    def test_no_setup_actions_returns_plugin_actions_when_set(self, plugin):
        mock_action = MagicMock()
        plugin.actions = [mock_action]

        with plugin.app.test_request_context():
            actions, error_response = plugin._get_checked_actions()

        plugin.actions = []
        assert actions == [mock_action]
        assert error_response is None

    def test_setup_actions_result_is_returned(self, plugin):
        mock_action = MagicMock()
        plugin.setup_actions = MagicMock(return_value=[mock_action])

        with plugin.app.test_request_context():
            actions, error_response = plugin._get_checked_actions()

        plugin.setup_actions = None
        assert actions == [mock_action]
        assert error_response is None

    def test_setup_actions_raises_returns_500(self, plugin):
        plugin.setup_actions = MagicMock(side_effect=RuntimeError("setup crashed"))

        with plugin.app.test_request_context():
            actions, error_response = plugin._get_checked_actions()

        plugin.setup_actions = None
        assert actions == []
        assert error_response is not None
        assert error_response.status_code == 500

    def test_setup_actions_raises_returns_error_body(self, plugin):
        plugin.setup_actions = MagicMock(side_effect=RuntimeError("setup crashed"))

        with plugin.app.test_request_context():
            _, error_response = plugin._get_checked_actions()

        plugin.setup_actions = None
        data = error_response.get_json()
        assert "api_error_message" in data
        assert "action setup" in data["api_error_message"].lower()

    def test_setup_actions_raises_logs_exception(self, plugin, caplog):
        plugin.setup_actions = MagicMock(side_effect=RuntimeError("setup crashed"))

        with caplog.at_level(logging.ERROR):
            with plugin.app.test_request_context():
                plugin._get_checked_actions()

        plugin.setup_actions = None
        assert any(r.levelno >= logging.ERROR for r in caplog.records)

    def test_setup_actions_token_validation_error_returns_401(self, plugin):
        plugin.setup_actions = MagicMock(return_value=[])
        plugin.validate_token = MagicMock(return_value=(None, "token expired"))

        with plugin.app.test_request_context():
            actions, error_response = plugin._get_checked_actions()

        plugin.setup_actions = None
        plugin.validate_token = None
        assert actions == []
        assert error_response is not None
        assert error_response.status_code == 401
