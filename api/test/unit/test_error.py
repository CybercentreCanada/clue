import re
from unittest.mock import MagicMock

from flask import Flask, g
from werkzeug.exceptions import InternalServerError

import clue.error as error


def _handle_500_with_value_error():
    try:
        raise ValueError("sensitive diagnostic")  # noqa: TRY301
    except ValueError as exc:
        return error.handle_500(InternalServerError(original_exception=exc))


def test_handle_500_hides_details_when_not_debug(monkeypatch):
    monkeypatch.setattr(error.config.api, "debug", False)
    monkeypatch.setenv("CLUE_VERSION", "1.2.3")
    logger_mock = MagicMock()
    monkeypatch.setattr(error, "logger", logger_mock)

    with Flask(__name__).test_request_context("/api/v1/lookup?type=ip"):
        g.user = {"uname": "jdoe"}
        response = _handle_500_with_value_error()

    response_message = response.json["api_error_message"]
    assert response.status_code == 500
    assert "sensitive diagnostic" not in response_message
    assert "raise ValueError" not in response_message

    match = re.fullmatch(r"An internal error has occurred \(ValueError\)\. Error ID: ([0-9a-f-]{36})", response_message)
    assert match is not None
    logger_mock.error.assert_called_once()
    log_call = logger_mock.error.call_args
    assert log_call.args[0] == (
        f"jdoe :: An internal error has occurred (ValueError) [1.2.3] (/api/v1/lookup?type=ip) :: {match.group(1)}"
    )
    assert log_call.kwargs["exc_info"] is True


def test_handle_500_returns_traceback_when_debug(monkeypatch):
    monkeypatch.setattr(error.config.api, "debug", True)

    with Flask(__name__).test_request_context():
        response = _handle_500_with_value_error()

    response_message = response.json["api_error_message"]
    assert response.status_code == 500
    assert "ValueError: sensitive diagnostic" in response_message
    assert "raise ValueError" in response_message
