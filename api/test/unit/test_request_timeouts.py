from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from pydantic import ValidationError

from clue.common.exceptions import InvalidDataException
from clue.common.timeouts import parse_timeout
from clue.config import config
from clue.models.actions import ActionSpec
from clue.models.config import API, ExternalSource
from clue.models.fetchers import FetcherDefinition
from clue.plugin.utils import Params
from clue.services import action_service, fetcher_service, lookup_service


@pytest.mark.parametrize(("value", "expected"), [(None, 5), ("2.5", 2.5), ("1e9", 10)])
def test_request_timeout_is_capped(value, expected):
    with Flask(__name__).test_request_context(query_string={} if value is None else {"max_timeout": value}):
        assert parse_timeout(5, maximum=10) == expected


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "0", "-1", "invalid"])
def test_request_timeout_rejects_invalid_values(value):
    with Flask(__name__).test_request_context(query_string={"max_timeout": value}):
        with pytest.raises(InvalidDataException) as error:
            parse_timeout(5, maximum=10)
    assert error.value.status_code == 400


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf")])
def test_config_rejects_invalid_timeout_limit(value):
    with pytest.raises(ValidationError):
        API(maximum_timeout_request=value)


@pytest.mark.parametrize("operation", ["execute_action", "get_action_status", "run_fetcher", "get_fetcher_status"])
def test_operation_uses_configured_timeout_limit(operation):
    is_action = "action" in operation
    is_status = "status" in operation
    service = action_service if is_action else fetcher_service
    plugin = ExternalSource(name="test", url="http://plugin/")
    user = {"uname": "test", "classification": "TLP:CLEAR"}
    identifier = "test_action" if is_action else "test_fetcher"
    metadata = (
        ActionSpec(id=identifier, name="Test", classification="TLP:CLEAR", supported_types={"ipv4"}, params={})
        if is_action
        else FetcherDefinition(
            id=identifier, classification="TLP:CLEAR", description="Test", format="json", supported_types={"ipv4"}
        )
    )
    result = (
        {"outcome": "success", "format": "json", "output": []}
        if is_action
        else {"outcome": "success", "format": "json", "data": {}}
    )
    response = MagicMock(ok=True)
    response.json.return_value = {"api_response": result}
    parameters = {} if is_action else {"type": "ipv4", "value": "127.0.0.1", "classification": "TLP:CLEAR"}
    args = ("test", identifier, "task", user) if is_status else ("test", identifier, user)
    metadata_name = "get_supported_actions" if is_action else "get_supported_fetchers"

    with (
        Flask(__name__).test_request_context(query_string={"max_timeout": "1e9"}, json=parameters),
        patch.object(config.api, "external_sources", [plugin]),
        patch.object(config.api, "maximum_timeout_request", 7.0),
        patch.object(service, metadata_name, return_value={identifier: metadata}),
        patch.object(service, "get_obo_access_token", return_value=(None, None)),
        patch.object(service, "request_with_safe_redirects", return_value=response) as upstream,
    ):
        getattr(service, operation)(*args)

    assert 0 < upstream.call_args.kwargs["timeout"] <= 7.0


def test_lookup_uses_configured_timeout_limit():
    with (
        Flask(__name__).test_request_context(query_string={"max_timeout": "1e9"}),
        patch.object(config.api, "maximum_timeout_request", 7.0),
    ):
        assert lookup_service.parse_timeout() == 7.0


def test_plugin_caps_timeout_and_deadline():
    with (
        Flask(__name__).test_request_context(query_string={"max_timeout": "1e9", "deadline": "1e12"}),
        patch("clue.plugin.utils.MAX_REQUEST_TIMEOUT", 7.0),
        patch("clue.plugin.utils.time.time", return_value=1000.0),
        patch("clue.plugin.utils.datetime") as clock,
    ):
        clock.now.return_value.timestamp.return_value = 1000.0
        params = Params.from_request()
    assert params.max_timeout == 7.0
    assert params.deadline == 1007.0


@pytest.mark.parametrize("parameter", [{"max_timeout": "nan"}, {"deadline": "inf"}])
def test_plugin_rejects_invalid_timeout_or_deadline(parameter):
    with Flask(__name__).test_request_context(query_string=parameter):
        with pytest.raises(InvalidDataException):
            Params.from_request()
