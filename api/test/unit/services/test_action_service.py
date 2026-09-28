from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from requests import exceptions

from clue.common.exceptions import NotFoundException
from clue.config import cache
from clue.models.actions import ActionSpec
from clue.models.config import ExternalSource
from clue.services import action_service


@pytest.mark.parametrize("operation", ["execute_action", "get_action_status"])
@pytest.mark.parametrize(
    "scenario",
    [
        "missing_plugin",
        "restricted_plugin",
        "missing_action",
        "empty_actions",
        "restricted_action",
        "authorized",
        "authorized_plugin",
    ],
)
def test_action_classification_authorization(operation, scenario):
    app = Flask(__name__)
    plugin = ExternalSource(name="test", url="http://plugin/", classification="TLP:CLEAR")
    action = ActionSpec(
        id="test_action", name="Test action", classification="TLP:AMBER", supported_types={"ipv4"}, params={}
    )
    user = {"uname": "test-user", "classification": "TLP:CLEAR"}
    if scenario in {"restricted_plugin", "authorized_plugin"}:
        plugin.classification = "TLP:AMBER"
    if scenario.startswith("authorized"):
        user["classification"] = "TLP:AMBER"
    actions = {"test_action": action}
    if scenario == "missing_action":
        actions = {"other_action": action}
    elif scenario == "empty_actions":
        actions = {}
    response = MagicMock()
    response.ok = True
    response.json.return_value = {
        "api_response": {"outcome": "success", "summary": "Completed", "format": "json", "output": []}
    }
    arguments = ("test", "test_action", user)
    if operation == "get_action_status":
        arguments = ("test", "test_action", "task-123", user)

    with (
        app.test_request_context(json={}, headers={"Authorization": "Bearer access-token"}),
        patch.object(action_service, "config") as configuration,
        patch.object(action_service, "get_supported_actions", return_value=actions) as get_supported,
        patch("clue.services.action_service.auth_service.check_obo", return_value=("obo-token", None)) as check_obo,
        patch.object(action_service, "generate_headers", return_value={"Authorization": "Bearer obo-token"}),
        patch(
            "clue.services.action_service.CLASSIFICATION.is_accessible",
            side_effect=lambda clearance, target: clearance == "TLP:AMBER" or target == "TLP:CLEAR",
        ) as is_accessible,
        patch("clue.services.action_service.requests.post", return_value=response) as post,
        patch("clue.services.action_service.requests.get", return_value=response) as get,
    ):
        configuration.api.external_sources = [] if scenario == "missing_plugin" else [plugin]
        if scenario.startswith("authorized"):
            result = getattr(action_service, operation)(*arguments)
            assert result.outcome == "success"
            is_accessible.assert_any_call("TLP:AMBER", "TLP:AMBER")
            upstream = post if operation == "execute_action" else get
            assert upstream.call_count == 1
            assert upstream.call_args.kwargs["headers"]["Authorization"] == "Bearer obo-token"
            assert upstream.call_args.args[0] == (
                "http://plugin/actions/test_action"
                if operation == "execute_action"
                else "http://plugin/actions/test_action/status/task-123"
            )
        else:
            with pytest.raises(NotFoundException) as error:
                getattr(action_service, operation)(*arguments)
            assert type(error.value) is NotFoundException
            assert error.value.status_code == 404
            assert str(error.value) == "Action not found."
            post.assert_not_called()
            get.assert_not_called()
            if scenario in {"missing_plugin", "restricted_plugin"}:
                get_supported.assert_not_called()
                check_obo.assert_not_called()
            elif scenario == "restricted_action":
                is_accessible.assert_any_call("TLP:CLEAR", "TLP:AMBER")


@pytest.mark.parametrize("clearance", ["TLP:CLEAR", "TLP:AMBER"])
def test_action_listing_filters_plugins_and_actions(clearance):
    app = Flask(__name__)
    user = {"uname": "test-user", "classification": clearance}
    public_plugin = ExternalSource(name="public", url="http://public/", classification="TLP:CLEAR")
    restricted_plugin = ExternalSource(name="restricted", url="http://restricted/", classification="TLP:AMBER")
    action = ActionSpec(
        id="public_action", name="Public action", classification="TLP:CLEAR", supported_types={"ipv4"}, params={}
    )
    restricted_action = action.model_copy(update={"id": "restricted_action", "classification": "TLP:AMBER"})
    with (
        app.test_request_context(headers={"Authorization": "Bearer access-token"}),
        patch.object(action_service, "config") as configuration,
        patch.object(
            action_service,
            "get_supported_actions",
            return_value={"public_action": action, "restricted_action": restricted_action},
        ) as get_supported,
        patch(
            "clue.services.action_service.CLASSIFICATION.is_accessible",
            side_effect=lambda user_clearance, target: user_clearance == "TLP:AMBER" or target == "TLP:CLEAR",
        ),
    ):
        configuration.api.external_sources = [public_plugin, restricted_plugin]
        result = action_service.get_plugins_supported_actions(user)

    if clearance == "TLP:CLEAR":
        assert result == {"public.public_action": action}
        get_supported.assert_called_once_with(public_plugin, user, access_token="access-token")
    else:
        assert result == {
            "public.public_action": action,
            "public.restricted_action": restricted_action,
            "restricted.public_action": action,
            "restricted.restricted_action": restricted_action,
        }
        assert get_supported.call_count == 2


@pytest.fixture
def cached_app():
    app = Flask(__name__)
    cache.init_app(app, config={"CACHE_TYPE": "SimpleCache"})
    return app


@pytest.fixture
def metadata_response():
    action = ActionSpec(
        id="test_action", name="Test action", classification="TLP:CLEAR", supported_types={"ipv4"}, params={}
    )
    response = MagicMock()
    response.ok = True
    response.json.return_value = {"api_response": {"test_action": action.model_dump()}}
    return response


def test_execute_and_status_refresh_metadata_and_do_one_obo_check_each(cached_app, metadata_response):
    plugin = ExternalSource(name="test", url="http://plugin/", classification="TLP:CLEAR")
    user = {"uname": "test-user", "classification": "TLP:CLEAR"}
    response = MagicMock()
    response.ok = True
    response.json.return_value = {"api_response": {"outcome": "success", "format": "json", "output": []}}

    with (
        patch.object(action_service, "config") as configuration,
        patch("clue.services.action_service.auth_service.check_obo", return_value=("obo-token", None)) as check_obo,
        patch("clue.services.action_service.CLASSIFICATION.is_accessible", return_value=True),
        patch.object(action_service, "generate_headers", return_value={"Authorization": "Bearer obo-token"}),
        patch(
            "clue.services.action_service.requests.get",
            side_effect=[metadata_response, metadata_response, response, metadata_response, response],
        ) as get,
        patch("clue.services.action_service.requests.post", return_value=response) as post,
    ):
        configuration.api.external_sources = [plugin]
        with cached_app.test_request_context(json={}, headers={"Authorization": "Bearer access-token"}):
            assert action_service.execute_action("test", "test_action", user).outcome == "success"
        for _poll in range(2):
            with cached_app.test_request_context(headers={"Authorization": "Bearer access-token"}):
                assert action_service.get_action_status("test", "test_action", "task-123", user).outcome == "success"

    assert check_obo.call_count == 3
    check_obo.assert_called_with(plugin, "access-token", "test-user")
    assert [entry.args[0] for entry in get.call_args_list] == [
        "http://plugin/actions/",
        "http://plugin/actions/",
        "http://plugin/actions/test_action/status/task-123",
        "http://plugin/actions/",
        "http://plugin/actions/test_action/status/task-123",
    ]
    assert post.call_count == 1


def test_action_metadata_is_refetched_for_same_caller(cached_app, metadata_response):
    plugin = ExternalSource(name="test", url="http://plugin/")
    user = {"uname": "test-user", "classification": "TLP:CLEAR"}
    headers = {"Authorization": "Bearer access-token"}
    with (
        cached_app.app_context(),
        patch("clue.services.action_service.requests.get", return_value=metadata_response) as get,
    ):
        first = action_service.get_supported_actions(plugin, user, headers=headers)
        assert action_service.get_supported_actions(plugin, user, headers=headers) == first
        assert get.call_count == 2


@pytest.mark.parametrize("failure", ["timeout", "http_error", "invalid_metadata", "empty"])
def test_action_metadata_failures_are_not_cached(cached_app, metadata_response, failure):
    plugin = ExternalSource(name="test", url="http://plugin/")
    user = {"uname": "test-user", "classification": "TLP:CLEAR"}
    failed_response = MagicMock()
    failed_response.ok = failure != "http_error"
    failed_response.status_code = 503
    failed_response.json.return_value = {
        "api_error_message": "Unavailable",
        "api_response": {} if failure == "empty" else {"test_action": {}},
    }
    if failure == "http_error":
        failed_response.json.return_value["api_response"] = metadata_response.json.return_value["api_response"]
    if failure == "timeout":
        failed_response = exceptions.Timeout()
    with (
        cached_app.app_context(),
        patch("clue.services.action_service.requests.get", side_effect=[failed_response, metadata_response]) as get,
    ):
        assert action_service.get_supported_actions(plugin, user, headers={}) == {}
        assert "test_action" in action_service.get_supported_actions(plugin, user, headers={})
        assert get.call_count == 2


@pytest.mark.parametrize("operation", ["execute_action", "get_action_status"])
def test_previous_action_metadata_does_not_bypass_obo_failure(cached_app, metadata_response, operation):
    plugin = ExternalSource(name="test", url="http://plugin/", classification="TLP:CLEAR")
    user = {"uname": "test-user", "classification": "TLP:CLEAR"}
    with (
        cached_app.test_request_context(json={}, headers={"Authorization": "Bearer access-token"}),
        patch.object(action_service, "config") as configuration,
        patch("clue.services.action_service.CLASSIFICATION.is_accessible", return_value=True),
        patch.object(action_service, "generate_headers", return_value={"Authorization": "Bearer obo-token"}),
        patch(
            "clue.services.action_service.auth_service.check_obo",
            side_effect=[("obo-token", None), (None, "Invalid token")],
        ) as check_obo,
        patch("clue.services.action_service.requests.get", return_value=metadata_response) as get,
        patch("clue.services.action_service.requests.post") as post,
    ):
        configuration.api.external_sources = [plugin]
        assert "test_action" in action_service.get_supported_actions(plugin, user, access_token="access-token")
        if operation == "execute_action":
            result = action_service.execute_action("test", "test_action", user)
        else:
            result = action_service.get_action_status("test", "test_action", "task-123", user)
        assert result.outcome == "failure"
        assert check_obo.call_count == 2
        assert get.call_count == 1
        post.assert_not_called()


@pytest.mark.parametrize("operation", ["execute_action", "get_action_status"])
@pytest.mark.parametrize("change", ["classification", "removed", "timeout", "http_error"])
def test_action_authorization_rechecks_metadata_after_success(cached_app, metadata_response, operation, change):
    plugin = ExternalSource(name="test", url="http://plugin/", classification="TLP:CLEAR")
    user = {"uname": "test-user", "classification": "TLP:CLEAR"}
    operation_response = MagicMock()
    operation_response.ok = True
    operation_response.json.return_value = {"api_response": {"outcome": "success", "format": "json", "output": []}}
    changed_response = MagicMock()
    changed_response.ok = change != "http_error"
    changed_response.status_code = 503
    changed_action = {
        **metadata_response.json.return_value["api_response"]["test_action"],
        "classification": "TLP:AMBER",
    }
    changed_response.json.return_value = {
        "api_response": {} if change == "removed" else {"test_action": changed_action},
        "api_error_message": "Unavailable",
    }
    if change == "timeout":
        changed_response = exceptions.Timeout()
    responses = [metadata_response, changed_response]
    arguments = ("test", "test_action", user)
    if operation == "get_action_status":
        responses = [metadata_response, operation_response, changed_response]
        arguments = ("test", "test_action", "task-123", user)

    with (
        cached_app.test_request_context(json={}, headers={"Authorization": "Bearer access-token"}),
        patch.object(action_service, "config") as configuration,
        patch("clue.services.action_service.auth_service.check_obo", return_value=("obo-token", None)) as check_obo,
        patch.object(action_service, "generate_headers", return_value={"Authorization": "Bearer obo-token"}),
        patch(
            "clue.services.action_service.CLASSIFICATION.is_accessible",
            side_effect=lambda clearance, target: clearance == "TLP:AMBER" or target == "TLP:CLEAR",
        ),
        patch("clue.services.action_service.requests.get", side_effect=responses) as get,
        patch("clue.services.action_service.requests.post", return_value=operation_response) as post,
    ):
        configuration.api.external_sources = [plugin]
        assert getattr(action_service, operation)(*arguments).outcome == "success"
        with pytest.raises(NotFoundException, match="^Action not found\\.$") as error:
            getattr(action_service, operation)(*arguments)

    assert error.value.status_code == 404
    assert check_obo.call_count == 2
    assert [entry.args[0] for entry in get.call_args_list] == (
        ["http://plugin/actions/", "http://plugin/actions/"]
        if operation == "execute_action"
        else ["http://plugin/actions/", "http://plugin/actions/test_action/status/task-123", "http://plugin/actions/"]
    )
    assert post.call_count == (1 if operation == "execute_action" else 0)
