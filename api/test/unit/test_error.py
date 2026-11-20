import pytest
from flask import Flask
from werkzeug.exceptions import InternalServerError

import clue.error as error


def _handle_500_with_value_error():
    try:
        raise ValueError("sensitive diagnostic")  # noqa: TRY301
    except ValueError as exc:
        return error.handle_500(InternalServerError(original_exception=exc))


@pytest.mark.parametrize(
    "debug,expected_message",
    [
        (False, "An Internal Error has occurred."),
        (True, None),
    ],
)
def test_handle_500_respects_debug_setting(monkeypatch, debug, expected_message):
    monkeypatch.setattr(error.config.api, "debug", debug)

    with Flask(__name__).test_request_context():
        response = _handle_500_with_value_error()

    response_message = response.json["api_error_message"]
    assert response.status_code == 500
    if expected_message is not None:
        assert response_message == expected_message
        assert "sensitive diagnostic" not in response_message
        assert "ValueError" not in response_message
    else:
        assert "ValueError: sensitive diagnostic" in response_message
        assert "raise ValueError" in response_message
