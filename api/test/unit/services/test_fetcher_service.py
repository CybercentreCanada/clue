from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from requests import exceptions

from clue.common.exceptions import AuthenticationException, ClueException, InvalidDataException, NotFoundException
from clue.config import cache
from clue.helper.obo import get_obo_access_token
from clue.models.config import ExternalSource
from clue.models.fetchers import FetcherDefinition, FetcherResult
from clue.services import fetcher_service


@pytest.fixture
def app():
    app = Flask(__name__)
    cache.init_app(app, config={"CACHE_TYPE": "SimpleCache"})
    return app


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


def test_get_obo_access_token_returns_none_without_authorization(app, plugin, user):
    with app.test_request_context():
        assert get_obo_access_token(plugin, user) == (None, None)


def test_get_obo_access_token_returns_caller_and_obo_tokens(app, plugin, user):
    with (
        app.test_request_context(headers={"Authorization": "Bearer access-token"}),
        patch("clue.helper.obo.auth_service.check_obo", return_value=("obo-token", None)) as check_obo,
    ):
        result = get_obo_access_token(plugin, user)

    assert result == ("access-token", "obo-token")
    check_obo.assert_called_once_with(plugin, "access-token", "test-user")


def test_get_obo_access_token_strips_basic_scheme(app, plugin, user):
    with (
        app.test_request_context(headers={"Authorization": "Basic api-key-credentials"}),
        patch("clue.helper.obo.auth_service.check_obo", return_value=(None, None)) as check_obo,
    ):
        result = get_obo_access_token(plugin, user)

    assert result == ("api-key-credentials", None)
    check_obo.assert_called_once_with(plugin, "api-key-credentials", "test-user")


def test_get_obo_access_token_rejects_invalid_token(app, plugin, user):
    with (
        app.test_request_context(headers={"Authorization": "Bearer access-token"}),
        patch("clue.helper.obo.auth_service.check_obo", return_value=(None, "invalid token")),
    ):
        with pytest.raises(AuthenticationException, match="Invalid token provided"):
            get_obo_access_token(plugin, user)


def test_get_supported_fetchers_parses_upstream_response(app, plugin, fetcher):
    response = make_response({"test_fetcher": fetcher.model_dump()})

    with app.app_context(), patch("clue.services.fetcher_service.requests.get", return_value=response) as get:
        result = fetcher_service.get_supported_fetchers(
            plugin, {"accept": "application/json", "content-type": "application/json"}
        )

    assert result == {"test_fetcher": fetcher}
    get.assert_called_once_with(
        "http://plugin/fetchers/",
        headers={"accept": "application/json", "content-type": "application/json"},
        timeout=5.0,
        allow_redirects=False,
    )


def test_all_supported_fetchers_skips_source_when_obo_fails(plugin, user):
    with (
        patch("clue.services.fetcher_service.config") as configuration,
        patch(
            "clue.services.fetcher_service.get_obo_access_token",
            side_effect=AuthenticationException("Invalid token provided for this enrichment."),
        ),
        patch("clue.services.fetcher_service.requests.get") as get,
    ):
        configuration.api.external_sources = [plugin]
        result = fetcher_service.all_supported_fetchers(user)

    assert result == {}
    get.assert_not_called()


def test_get_supported_fetchers_returns_empty_for_invalid_upstream_response(app, plugin):
    response = make_response({})
    response.json.return_value = {"unexpected": "response"}

    with app.app_context(), patch("clue.services.fetcher_service.requests.get", return_value=response):
        result = fetcher_service.get_supported_fetchers(
            plugin, {"accept": "application/json", "content-type": "application/json"}
        )

    assert result == {}


@pytest.mark.parametrize("failure", ["timeout", "http_error"])
def test_get_supported_fetchers_can_fail_closed_when_metadata_is_unavailable(app, plugin, failure):
    if failure == "timeout":
        request = patch("clue.services.fetcher_service.requests.get", side_effect=exceptions.Timeout())
    else:
        request = patch(
            "clue.services.fetcher_service.requests.get",
            return_value=make_response({}, ok=False, status_code=503),
        )

    with app.app_context(), request as get:
        with pytest.raises(ClueException, match="Unable to verify fetcher availability") as error:
            fetcher_service.get_supported_fetchers(
                plugin,
                {"accept": "application/json", "content-type": "application/json"},
                timeout=2.0,
                raise_on_error=True,
            )

    assert error.value.status_code == 503
    get.assert_called_once_with(
        "http://plugin/fetchers/",
        headers={"accept": "application/json", "content-type": "application/json"},
        timeout=2.0,
        allow_redirects=False,
    )


def test_all_supported_fetchers_prefixes_fetcher_ids(user, plugin, fetcher):
    other_plugin = ExternalSource(name="other", url="http://other/")
    other_fetcher = fetcher.model_copy(update={"id": "other_fetcher"})

    with (
        patch("clue.services.fetcher_service.config") as mock_config,
        patch(
            "clue.services.fetcher_service.get_supported_fetchers",
            side_effect=[{"test_fetcher": fetcher}, {"other_fetcher": other_fetcher}],
        ) as get_supported,
        patch(
            "clue.services.fetcher_service.get_obo_access_token",
            side_effect=[("access-token", "obo-token"), ("access-token", "obo-token")],
        ),
    ):
        mock_config.api.external_sources = [plugin, other_plugin]
        result = fetcher_service.all_supported_fetchers(user)

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
    all_supported.assert_called_once_with(user)


@pytest.mark.parametrize("clearance", ["TLP:CLEAR", "TLP:AMBER"])
def test_fetcher_listing_filters_plugins_and_fetchers(app, user, plugin, fetcher, clearance):
    user["classification"] = clearance
    plugin.classification = "TLP:CLEAR"
    restricted_plugin = ExternalSource(name="restricted", url="http://restricted/", classification="TLP:AMBER")
    restricted_fetcher = fetcher.model_copy(update={"id": "restricted_fetcher", "classification": "TLP:AMBER"})
    with (
        app.test_request_context(headers={"Authorization": "Bearer access-token"}),
        patch.object(fetcher_service, "config") as configuration,
        patch(
            "clue.services.fetcher_service.get_obo_access_token",
            return_value=("access-token", "obo-token"),
        ),
        patch.object(
            fetcher_service,
            "get_supported_fetchers",
            return_value={"test_fetcher": fetcher, "restricted_fetcher": restricted_fetcher},
        ) as get_supported,
        patch(
            "clue.services.fetcher_service.CLASSIFICATION.is_accessible",
            side_effect=lambda user_clearance, target: user_clearance == "TLP:AMBER" or target == "TLP:CLEAR",
        ),
    ):
        configuration.api.external_sources = [plugin, restricted_plugin]
        result = fetcher_service.get_plugins_supported_fetchers(user)

    if clearance == "TLP:CLEAR":
        assert result == {"test.test_fetcher": fetcher}
        get_supported.assert_called_once_with(
            plugin,
            {
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": "Bearer obo-token",
                "X-Clue-Authorization": "access-token",
            },
        )
    else:
        assert result == {
            "test.test_fetcher": fetcher,
            "test.restricted_fetcher": restricted_fetcher,
            "restricted.test_fetcher": fetcher,
            "restricted.restricted_fetcher": restricted_fetcher,
        }
        assert get_supported.call_count == 2


def test_run_fetcher_returns_upstream_result(app, configured_plugin, user, fetcher):
    response = make_response({"outcome": "success", "data": {"result": "ok"}, "format": "json"})
    parameters = {"type": "ipv4", "value": "127.0.0.1", "classification": "TLP:CLEAR"}

    with (
        app.test_request_context(json=parameters, headers={"Authorization": "Bearer access-token"}),
        patch("clue.helper.obo.auth_service.check_obo", return_value=("obo-token", None)),
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
        headers={
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": "Bearer obo-token",
            "X-Clue-Authorization": "access-token",
        },
        timeout=60.0,
        allow_redirects=False,
    )


def test_run_fetcher_rejects_selector_above_fetcher_classification(app, configured_plugin, user, fetcher):
    with (
        app.test_request_context(json={"type": "ipv4", "value": "127.0.0.1", "classification": "TLP:AMBER"}),
        patch("clue.services.fetcher_service.get_supported_fetchers", return_value={"test_fetcher": fetcher}),
        patch(
            "clue.services.fetcher_service.CLASSIFICATION.is_accessible", side_effect=[True, True, False]
        ) as is_accessible,
        patch("clue.services.fetcher_service.requests.post") as post,
    ):
        with pytest.raises(InvalidDataException, match="Cannot send data classified as TLP:AMBER") as error:
            fetcher_service.run_fetcher("test", "test_fetcher", user)

    assert error.value.status_code == 400
    is_accessible.assert_called_with("TLP:CLEAR", "TLP:AMBER")
    assert is_accessible.call_count == 3
    post.assert_not_called()


def test_run_fetcher_rejects_unknown_plugin(app, user):
    with app.test_request_context(), patch("clue.services.fetcher_service.config") as mock_config:
        mock_config.api.external_sources = []

        with pytest.raises(NotFoundException, match="Fetcher not found"):
            fetcher_service.run_fetcher("unknown", "test_fetcher", user)


def test_run_fetcher_rejects_invalid_obo_token(app, configured_plugin, user):
    with (
        app.test_request_context(headers={"Authorization": "Bearer access-token"}),
        patch("clue.helper.obo.auth_service.check_obo", return_value=(None, "invalid token")),
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


def test_run_fetcher_wraps_timeout_errors(app, configured_plugin, user, fetcher):
    with (
        app.test_request_context(json={"type": "ipv4", "value": "127.0.0.1"}),
        patch("clue.services.fetcher_service.get_supported_fetchers", return_value={"test_fetcher": fetcher}),
        patch("clue.services.fetcher_service.CLASSIFICATION.is_accessible", return_value=True),
        patch("clue.services.fetcher_service.requests.post", side_effect=exceptions.Timeout),
    ):
        with pytest.raises(ClueException, match="Timeout"):
            fetcher_service.run_fetcher("test", "test_fetcher", user)


def test_get_fetcher_status_returns_upstream_result(app, configured_plugin, user, fetcher):
    response = make_response({"outcome": "success", "data": {"result": "ok"}, "format": "json"})

    with (
        app.test_request_context(query_string={"max_timeout": "12.5"}),
        patch("clue.services.fetcher_service.get_supported_fetchers", return_value={"test_fetcher": fetcher}),
        patch("clue.services.fetcher_service.monotonic", side_effect=[0.0, 2.5]),
        patch("clue.services.fetcher_service.requests.get", return_value=response) as get,
    ):
        result = fetcher_service.get_fetcher_status("test", "test_fetcher", "task-123", user)

    assert result.outcome == "success"
    get.assert_called_once_with(
        "http://plugin/fetchers/test_fetcher/status/task-123",
        headers={"accept": "application/json", "content-type": "application/json"},
        timeout=10.0,
        allow_redirects=False,
    )


def test_get_fetcher_status_wraps_connection_errors(app, configured_plugin, user, fetcher):
    with (
        app.test_request_context(),
        patch("clue.services.fetcher_service.get_supported_fetchers", return_value={"test_fetcher": fetcher}),
        patch("clue.services.fetcher_service.requests.get", side_effect=exceptions.ConnectionError),
    ):
        with pytest.raises(ClueException, match="ConnectionError"):
            fetcher_service.get_fetcher_status("test", "test_fetcher", "task-123", user)


@pytest.mark.parametrize("operation", ["run_fetcher", "get_fetcher_status"])
@pytest.mark.parametrize(
    "scenario",
    [
        "missing_plugin",
        "restricted_plugin",
        "missing_fetcher",
        "empty_fetchers",
        "restricted_fetcher",
        "authorized",
        "authorized_plugin",
    ],
)
def test_fetcher_classification_authorization(app, plugin, user, fetcher, operation, scenario):
    plugin.classification = "TLP:CLEAR"
    fetcher.classification = "TLP:AMBER"
    if scenario in {"restricted_plugin", "authorized_plugin"}:
        plugin.classification = "TLP:AMBER"
    if scenario.startswith("authorized"):
        user["classification"] = "TLP:AMBER"
    fetchers = {"test_fetcher": fetcher}
    if scenario == "missing_fetcher":
        fetchers = {"other_fetcher": fetcher}
    elif scenario == "empty_fetchers":
        fetchers = {}
    response = make_response({"outcome": "success", "data": {"result": "ok"}, "format": "json"})
    arguments = ("test", "test_fetcher", user)
    if operation == "get_fetcher_status":
        arguments = ("test", "test_fetcher", "task-123", user)

    with (
        app.test_request_context(
            json={"type": "ipv4", "value": "127.0.0.1", "classification": "TLP:CLEAR"},
            headers={"Authorization": "Bearer access-token"},
        ),
        patch.object(fetcher_service, "config") as configuration,
        patch.object(fetcher_service, "get_supported_fetchers", return_value=fetchers) as get_supported,
        patch("clue.helper.obo.auth_service.check_obo", return_value=("obo-token", None)) as check_obo,
        patch(
            "clue.services.fetcher_service.CLASSIFICATION.is_accessible",
            side_effect=lambda clearance, target: clearance == "TLP:AMBER" or target == "TLP:CLEAR",
        ) as is_accessible,
        patch("clue.services.fetcher_service.requests.post", return_value=response) as post,
        patch("clue.services.fetcher_service.requests.get", return_value=response) as get,
    ):
        configuration.api.external_sources = [] if scenario == "missing_plugin" else [plugin]
        if scenario.startswith("authorized"):
            result = getattr(fetcher_service, operation)(*arguments)
            assert result.outcome == "success"
            assert result.data == {"result": "ok"}
            is_accessible.assert_any_call("TLP:AMBER", "TLP:AMBER")
            upstream = post if operation == "run_fetcher" else get
            assert upstream.call_count == 1
            assert upstream.call_args.kwargs["headers"]["Authorization"] == "Bearer obo-token"
            assert upstream.call_args.args[0] == (
                "http://plugin/fetchers/test_fetcher"
                if operation == "run_fetcher"
                else "http://plugin/fetchers/test_fetcher/status/task-123"
            )
        else:
            with pytest.raises(NotFoundException) as error:
                getattr(fetcher_service, operation)(*arguments)
            assert type(error.value) is NotFoundException
            assert error.value.status_code == 404
            assert str(error.value) == "Fetcher not found."
            post.assert_not_called()
            get.assert_not_called()
            if scenario in {"missing_plugin", "restricted_plugin"}:
                get_supported.assert_not_called()
                check_obo.assert_not_called()
            elif scenario == "restricted_fetcher":
                is_accessible.assert_any_call("TLP:CLEAR", "TLP:AMBER")


@pytest.mark.parametrize("operation", ["get_plugins_supported_fetchers", "run_fetcher", "get_fetcher_status"])
@pytest.mark.parametrize("change", ["classification", "removed", "timeout", "http_error"])
def test_fetcher_metadata_is_refreshed_after_success(app, configured_plugin, user, fetcher, operation, change):
    metadata = make_response({"test_fetcher": fetcher.model_dump()})
    result_response = make_response({"outcome": "success", "data": {"result": "ok"}, "format": "json"})
    changed_fetcher = fetcher.model_copy(update={"classification": "TLP:AMBER"})
    changed_response = make_response({"test_fetcher": changed_fetcher.model_dump()})
    if change == "removed":
        changed_response = make_response({})
    elif change == "timeout":
        changed_response = exceptions.Timeout()
    elif change == "http_error":
        changed_response = make_response(
            {"test_fetcher": fetcher.model_dump()}, ok=False, status_code=503, error_message="Unavailable"
        )
    responses = [metadata, changed_response]
    arguments = ("test", "test_fetcher", user)
    if operation == "get_plugins_supported_fetchers":
        arguments = (user,)
    elif operation == "get_fetcher_status":
        responses = [metadata, result_response, changed_response]
        arguments = ("test", "test_fetcher", "task-123", user)

    with (
        patch("clue.helper.obo.auth_service.check_obo", return_value=("obo-token", None)) as check_obo,
        patch(
            "clue.services.fetcher_service.CLASSIFICATION.is_accessible",
            side_effect=lambda clearance, target: clearance == "TLP:AMBER" or target == "TLP:CLEAR",
        ),
        patch("clue.services.fetcher_service.requests.get", side_effect=responses) as get,
        patch("clue.services.fetcher_service.requests.post", return_value=result_response) as post,
    ):
        for attempt in range(2):
            with app.test_request_context(
                json={"type": "ipv4", "value": "127.0.0.1", "classification": "TLP:CLEAR"},
                headers={"Authorization": "Bearer access-token"},
            ):
                if operation == "get_plugins_supported_fetchers":
                    result = getattr(fetcher_service, operation)(*arguments)
                    assert result == ({"test.test_fetcher": fetcher} if attempt == 0 else {})
                elif attempt == 0:
                    assert getattr(fetcher_service, operation)(*arguments).outcome == "success"
                elif operation == "get_fetcher_status" and change in {"timeout", "http_error"}:
                    with pytest.raises(ClueException, match="Unable to verify fetcher availability") as error:
                        getattr(fetcher_service, operation)(*arguments)
                    assert error.value.status_code == 503
                else:
                    with pytest.raises(NotFoundException, match="^Fetcher not found\\.$") as error:
                        getattr(fetcher_service, operation)(*arguments)
                    assert error.value.status_code == 404

    assert check_obo.call_count == 2
    assert [entry.args[0] for entry in get.call_args_list] == (
        ["http://plugin/fetchers/", "http://plugin/fetchers/test_fetcher/status/task-123", "http://plugin/fetchers/"]
        if operation == "get_fetcher_status"
        else ["http://plugin/fetchers/", "http://plugin/fetchers/"]
    )
    for entry in get.call_args_list:
        assert entry.kwargs["headers"]["Authorization"] == "Bearer obo-token"
    assert post.call_count == (1 if operation == "run_fetcher" else 0)


@pytest.mark.parametrize("operation", ["get_plugins_supported_fetchers", "run_fetcher", "get_fetcher_status"])
def test_previous_fetcher_metadata_does_not_bypass_token_failure(app, configured_plugin, user, fetcher, operation):
    metadata = make_response({"test_fetcher": fetcher.model_dump()})
    with (
        app.test_request_context(
            json={"type": "ipv4", "value": "127.0.0.1", "classification": "TLP:CLEAR"},
            headers={"Authorization": "Bearer access-token"},
        ),
        patch("clue.services.fetcher_service.CLASSIFICATION.is_accessible", return_value=True),
        patch(
            "clue.helper.obo.auth_service.check_obo",
            side_effect=[("obo-token", None), (None, "Invalid token")],
        ) as check_obo,
        patch("clue.services.fetcher_service.requests.get", return_value=metadata) as get,
        patch("clue.services.fetcher_service.requests.post") as post,
    ):
        assert fetcher_service.get_plugins_supported_fetchers(user) == {"test.test_fetcher": fetcher}
        if operation == "get_plugins_supported_fetchers":
            assert fetcher_service.get_plugins_supported_fetchers(user) == {}
        else:
            arguments = ("test", "test_fetcher", user)
            if operation == "get_fetcher_status":
                arguments = ("test", "test_fetcher", "task-123", user)
            with pytest.raises(AuthenticationException, match="Invalid token provided"):
                getattr(fetcher_service, operation)(*arguments)

    assert check_obo.call_count == 2
    get.assert_called_once_with(
        "http://plugin/fetchers/",
        headers={
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": "Bearer obo-token",
            "X-Clue-Authorization": "access-token",
        },
        timeout=5.0,
        allow_redirects=False,
    )
    post.assert_not_called()
