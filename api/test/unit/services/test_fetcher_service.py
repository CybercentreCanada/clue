from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from requests import exceptions

from clue.common.exceptions import AuthenticationException, ClueException, InvalidDataException, NotFoundException
from clue.models.config import ExternalSource
from clue.models.fetchers import FetcherDefinition, FetcherResult
from clue.services import fetcher_service


@pytest.fixture
def app():
    return Flask(__name__)


@pytest.fixture
def user():
    return {"uname": "test-user", "classification": "TLP:CLEAR"}


@pytest.fixture
def plugin():
    return ExternalSource(name="test", url="http://plugin/")


@pytest.fixture
def fetcher():
    return FetcherDefinition(
        id="test_fetcher",
        classification="TLP:CLEAR",
        description="Test fetcher",
        format="json",
        supported_types={"ipv4"},
    )


@pytest.fixture
def configured_plugin(plugin):
    with patch("clue.services.fetcher_service.config") as mock_config:
        mock_config.api.external_sources = [plugin]
        yield plugin


def make_response(api_response, *, ok=True, status_code=200, error_message=None):
    response = MagicMock()
    response.ok = ok
    response.status_code = status_code
    response.json.return_value = {
        "api_response": api_response,
        "api_error_message": error_message,
    }
    return response


def get_supported_fetchers_uncached(plugin, user, access_token=None):
    uncached = getattr(fetcher_service.get_supported_fetchers, "uncached")
    return uncached(plugin, user, access_token=access_token)


def test_get_obo_access_token_returns_none_without_authorization(app, plugin, user):
    with app.test_request_context():
        assert fetcher_service.get_obo_access_token(plugin, user) == (None, None)


def test_get_obo_access_token_returns_caller_and_obo_tokens(app, plugin, user):
    with (
        app.test_request_context(headers={"Authorization": "Bearer access-token"}),
        patch("clue.services.fetcher_service.auth_service.check_obo", return_value=("obo-token", None)) as check_obo,
    ):
        result = fetcher_service.get_obo_access_token(plugin, user)

    assert result == ("access-token", "obo-token")
    check_obo.assert_called_once_with(plugin, "access-token", "test-user")


def test_get_obo_access_token_rejects_invalid_token(app, plugin, user):
    with (
        app.test_request_context(headers={"Authorization": "Bearer access-token"}),
        patch("clue.services.fetcher_service.auth_service.check_obo", return_value=(None, "invalid token")),
    ):
        with pytest.raises(AuthenticationException, match="Invalid token provided"):
            fetcher_service.get_obo_access_token(plugin, user)


def test_get_supported_fetchers_parses_upstream_response(plugin, user, fetcher):
    response = make_response({"test_fetcher": fetcher.model_dump()})

    with patch("clue.services.fetcher_service.requests.get", return_value=response) as get:
        result = get_supported_fetchers_uncached(plugin, user)

    assert result == {"test_fetcher": fetcher}
    get.assert_called_once_with("http://plugin/fetchers/", headers={"Accept": "application/json"}, timeout=5.0)


def test_get_supported_fetchers_returns_empty_when_obo_fails(plugin, user):
    with (
        patch("clue.services.fetcher_service.auth_service.check_obo", return_value=(None, "invalid token")),
        patch("clue.services.fetcher_service.requests.get") as get,
    ):
        result = get_supported_fetchers_uncached(plugin, user, access_token="access-token")

    assert result == {}
    get.assert_not_called()


def test_get_supported_fetchers_returns_empty_for_invalid_upstream_response(plugin, user):
    response = make_response({})
    response.json.return_value = {"unexpected": "response"}

    with patch("clue.services.fetcher_service.requests.get", return_value=response):
        result = get_supported_fetchers_uncached(plugin, user)

    assert result == {}


def test_all_supported_fetchers_prefixes_fetcher_ids(user, plugin, fetcher):
    other_plugin = ExternalSource(name="other", url="http://other/")
    other_fetcher = fetcher.model_copy(update={"id": "other_fetcher"})

    with (
        patch("clue.services.fetcher_service.config") as mock_config,
        patch(
            "clue.services.fetcher_service.get_supported_fetchers",
            side_effect=[{"test_fetcher": fetcher}, {"other_fetcher": other_fetcher}],
        ) as get_supported,
    ):
        mock_config.api.external_sources = [plugin, other_plugin]
        result = fetcher_service.all_supported_fetchers(user, access_token="access-token")

    assert result == {
        "test.test_fetcher": fetcher,
        "other.other_fetcher": other_fetcher,
    }
    assert get_supported.call_count == 2


def test_get_plugins_supported_fetchers_filters_inaccessible_fetchers(app, user, fetcher):
    restricted_fetcher = fetcher.model_copy(update={"id": "restricted_fetcher", "classification": "TLP:AMBER"})

    with (
        app.test_request_context(headers={"Authorization": "Bearer access-token"}),
        patch(
            "clue.services.fetcher_service.all_supported_fetchers",
            return_value={
                "test.test_fetcher": fetcher,
                "test.restricted_fetcher": restricted_fetcher,
            },
        ) as all_supported,
        patch(
            "clue.services.fetcher_service.CLASSIFICATION.is_accessible",
            side_effect=lambda _user_classification, classification: classification == "TLP:CLEAR",
        ),
    ):
        result = fetcher_service.get_plugins_supported_fetchers(user)

    assert result == {"test.test_fetcher": fetcher}
    all_supported.assert_called_once_with(user, access_token="access-token")


def test_run_fetcher_returns_upstream_result(app, configured_plugin, user, fetcher):
    response = make_response({"outcome": "success", "data": {"result": "ok"}, "format": "json"})
    parameters = {"type": "ipv4", "value": "127.0.0.1", "classification": "TLP:CLEAR"}

    with (
        app.test_request_context(json=parameters, headers={"Authorization": "Bearer access-token"}),
        patch("clue.services.fetcher_service.auth_service.check_obo", return_value=("obo-token", None)),
        patch("clue.services.fetcher_service.get_supported_fetchers", return_value={"test_fetcher": fetcher}),
        patch("clue.services.fetcher_service.CLASSIFICATION.is_accessible", return_value=True),
        patch("clue.services.fetcher_service.requests.post", return_value=response) as post,
    ):
        result = fetcher_service.run_fetcher("test", "test_fetcher", user)

    assert isinstance(result, FetcherResult)
    assert result.outcome == "success"
    assert result.data == {"result": "ok"}
    post.assert_called_once_with(
        "http://plugin/fetchers/test_fetcher",
        json=parameters,
        headers={"Accept": "application/json", "Authorization": "Bearer obo-token"},
        timeout=60.0,
    )


def test_run_fetcher_rejects_selector_above_fetcher_classification(app, configured_plugin, user, fetcher):
    with (
        app.test_request_context(json={"type": "ipv4", "value": "127.0.0.1", "classification": "TLP:AMBER"}),
        patch("clue.services.fetcher_service.get_supported_fetchers", return_value={"test_fetcher": fetcher}),
        patch("clue.services.fetcher_service.CLASSIFICATION.is_accessible", return_value=False) as is_accessible,
        patch("clue.services.fetcher_service.requests.post") as post,
    ):
        with pytest.raises(InvalidDataException, match="Cannot send data classified as TLP:AMBER") as error:
            fetcher_service.run_fetcher("test", "test_fetcher", user)

    assert error.value.status_code == 400
    is_accessible.assert_called_once_with("TLP:CLEAR", "TLP:AMBER")
    post.assert_not_called()


def test_run_fetcher_rejects_unknown_plugin(app, user):
    with app.test_request_context(), patch("clue.services.fetcher_service.config") as mock_config:
        mock_config.api.external_sources = []

        with pytest.raises(NotFoundException, match="Plugin unknown does not exist"):
            fetcher_service.run_fetcher("unknown", "test_fetcher", user)


def test_run_fetcher_rejects_invalid_obo_token(app, configured_plugin, user):
    with (
        app.test_request_context(headers={"Authorization": "Bearer access-token"}),
        patch("clue.services.fetcher_service.auth_service.check_obo", return_value=(None, "invalid token")),
    ):
        with pytest.raises(AuthenticationException, match="Invalid token provided"):
            fetcher_service.run_fetcher("test", "test_fetcher", user)


def test_run_fetcher_rejects_invalid_selector(app, configured_plugin, user):
    with (
        app.test_request_context(json={}),
        patch("clue.services.fetcher_service.get_supported_fetchers") as get_supported,
    ):
        with pytest.raises(InvalidDataException, match="Validation error encountered on request body") as error:
            fetcher_service.run_fetcher("test", "test_fetcher", user)

    assert error.value.status_code == 400
    get_supported.assert_not_called()


def test_run_fetcher_raises_upstream_error(app, configured_plugin, user, fetcher):
    response = make_response({}, ok=False, status_code=502, error_message="Plugin failure")

    with (
        app.test_request_context(json={"type": "ipv4", "value": "127.0.0.1"}),
        patch("clue.services.fetcher_service.get_supported_fetchers", return_value={"test_fetcher": fetcher}),
        patch("clue.services.fetcher_service.CLASSIFICATION.is_accessible", return_value=True),
        patch("clue.services.fetcher_service.requests.post", return_value=response),
    ):
        with pytest.raises(ClueException, match="Plugin failure") as error:
            fetcher_service.run_fetcher("test", "test_fetcher", user)

    assert error.value.status_code == 502


def test_run_fetcher_wraps_connection_errors(app, configured_plugin, user, fetcher):
    with (
        app.test_request_context(json={"type": "ipv4", "value": "127.0.0.1"}),
        patch("clue.services.fetcher_service.get_supported_fetchers", return_value={"test_fetcher": fetcher}),
        patch("clue.services.fetcher_service.CLASSIFICATION.is_accessible", return_value=True),
        patch("clue.services.fetcher_service.requests.post", side_effect=exceptions.ConnectionError),
    ):
        with pytest.raises(ClueException, match="ConnectionError"):
            fetcher_service.run_fetcher("test", "test_fetcher", user)


def test_get_fetcher_status_returns_upstream_result(app, configured_plugin, user):
    response = make_response({"outcome": "success", "data": {"result": "ok"}, "format": "json"})

    with (
        app.test_request_context(query_string={"max_timeout": "12.5"}),
        patch("clue.services.fetcher_service.requests.get", return_value=response) as get,
    ):
        result = fetcher_service.get_fetcher_status("test", "test_fetcher", "task-123", user)

    assert result.outcome == "success"
    get.assert_called_once_with(
        "http://plugin/fetchers/test_fetcher/status/task-123",
        headers={"Accept": "application/json"},
        timeout=12.5,
    )


def test_get_fetcher_status_wraps_connection_errors(app, configured_plugin, user):
    with (
        app.test_request_context(),
        patch("clue.services.fetcher_service.requests.get", side_effect=exceptions.ConnectionError),
    ):
        with pytest.raises(ClueException, match="ConnectionError"):
            fetcher_service.get_fetcher_status("test", "test_fetcher", "task-123", user)
