from unittest.mock import MagicMock, patch
from urllib.parse import quote, unquote, urlsplit

import pytest
from flask import Flask
from requests import Request, exceptions

from clue.common.exceptions import AuthenticationException, ClueException, ClueValueError, NotFoundException
from clue.config import cache, config
from clue.helper.obo import get_obo_access_token
from clue.models.actions import ActionResult, ActionSpec
from clue.models.auth_user import AuthResult, AuthUser, Privilege
from clue.models.config import ExternalSource
from clue.services import action_service


@pytest.mark.parametrize(
    ("operation", "target"),
    [("execute_action", "action"), ("get_action_status", "action")],
)
@pytest.mark.parametrize(
    ("payload", "encoded"),
    [
        ("..", None),
        (".", None),
        ("", None),
        ("../admin/keys", None),
        ("x?role=admin", None),
        ("../../etc/passwd", None),
        ("../../../shutdown", None),
        ("x#fragment", None),
        ("%2e%2e%2fadmin", None),
        ("//attacker.invalid/admin", None),
        ("x\\admin", None),
        ("x..y", None),
        ("x.y", "x%2Ey"),
        ("test_action-123", "test_action-123"),
    ],
)
def test_action_urls_keep_identifiers_in_one_path_segment(operation, target, payload, encoded):
    app = Flask(__name__)
    plugin = ExternalSource(name="test", url="http://plugin.internal:8080/api/")
    user = {"uname": "test-user", "classification": "TLP:CLEAR"}
    action_id = payload if target == "action" else "test_action"
    task_id = payload if target == "task" else "task-123"
    action = ActionSpec(
        id="test_action", name="Test action", classification="TLP:CLEAR", supported_types={"ipv4"}, params={}
    )
    response = MagicMock(status_code=200, ok=True)
    response.json.return_value = {"api_response": {"outcome": "success", "format": "json", "output": []}}

    with (
        app.test_request_context(json={}),
        patch.object(action_service, "config") as configuration,
        patch.object(action_service, "get_supported_actions", return_value={action_id: action}) as metadata,
        patch.object(action_service, "get_obo_access_token", return_value=(None, None)) as obo,
        patch.object(action_service, "generate_headers", return_value={}),
        patch.object(action_service.requests, "post", return_value=response) as post,
        patch.object(action_service.requests, "get", return_value=response) as get,
    ):
        configuration.api.external_sources = [plugin]
        arguments = ("test", action_id, user) if operation == "execute_action" else ("test", action_id, task_id, user)
        if encoded is None:
            with pytest.raises(ClueValueError) as error:
                getattr(action_service, operation)(*arguments)
            assert error.value.status_code == 400
            metadata.assert_not_called()
            obo.assert_not_called()
            post.assert_not_called()
            get.assert_not_called()
            return

        assert getattr(action_service, operation)(*arguments).outcome == "success"
        upstream = post if operation == "execute_action" else get
        upstream.assert_called_once()
        path = f"/api/actions/{encoded}" if target == "action" else f"/api/actions/test_action/status/{encoded}"
        if operation == "get_action_status" and target == "action":
            path += "/status/task-123"
        url = upstream.call_args.args[0]
        assert url == f"http://plugin.internal:8080{path}"
        for candidate in (url, Request("GET", url).prepare().url):
            parsed = urlsplit(candidate)
            assert (parsed.scheme, parsed.netloc) == ("http", "plugin.internal:8080")
            assert parsed.path.startswith("/api/actions/")
            assert len(parsed.path.split("/")) == len(path.split("/"))
            assert all(segment not in {".", ".."} for segment in parsed.path.split("/"))
            assert not parsed.query
            assert not parsed.fragment


@pytest.mark.parametrize(
    ("operation", "target"),
    [("execute_action", "action"), ("get_action_status", "action")],
)
@pytest.mark.parametrize(
    "payload",
    [
        "",
        ".",
        "..",
        "../admin/keys",
        "x?role=admin",
        "../../etc/passwd",
        "../../../shutdown",
        "x#fragment",
        "%2e%2e%2fadmin",
        "x\\admin",
        "x..y",
        "plugin.action",
        "Safe_id-123",
    ],
)
def test_action_routes_validate_identifiers_before_calling_service(operation, target, payload):
    from clue.api.v1.actions import actions_api

    app = Flask(__name__)
    app.testing = True
    app.register_blueprint(actions_api)
    action_id = quote(payload, safe="") if target == "action" else "test_action"
    task_id = quote(payload, safe="") if target == "task" else "task-123"
    path = (
        f"/api/v1/actions/execute/test/{action_id}"
        if operation == "execute_action"
        else f"/api/v1/actions/test/{action_id}/status/{task_id}"
    )
    auth_result = AuthResult(
        user=AuthUser(uname="test-user", classification="TLP:CLEAR"),
        privileges={Privilege.READ, Privilege.WRITE},
    )
    with (
        patch("clue.security.auth_service.bearer_auth", return_value=auth_result),
        patch.object(config.api, "audit", False),
        patch.object(config.ui, "replication", False),
        patch.object(
            action_service, operation, return_value=ActionResult(outcome="success", format="json", output=[])
        ) as service,
        app.test_client() as client,
    ):
        response = client.open(
            path,
            method="POST" if operation == "execute_action" else "GET",
            headers={"Authorization": "Bearer test-token"},
            json={},
        )
    if payload in {"Safe_id-123", "plugin.action"}:
        assert response.status_code == 200
        service.assert_called_once()
        assert service.call_args.args[1 if target == "action" else 2] == payload
    else:
        assert response.status_code in {400, 404}
        service.assert_not_called()


LEGACY_TASK_IDS = [
    "550e8400-e29b-41d4-a716-446655440000",
    "task-123",
    "abc:123",
    "job@worker",
    "YWJj==",
    "x.y",
    "x..y",
    "...",
    "x?role=admin",
    "x#fragment",
    "%2e%2e%2fadmin",
    "x\\admin",
    "x y",
    "caf\u00e9",
]
BAD_TASK_IDS = ["", ".", "..", "a/b", "../admin/keys", "//attacker.invalid/admin", "x\n", "x\x00", "a" * 257]


def _task_status_context(app, plugin, user, responses):
    from contextlib import ExitStack

    action = ActionSpec(
        id="test_action", name="Test action", classification="TLP:CLEAR", supported_types={"ipv4"}, params={}
    )
    stack = ExitStack()
    stack.enter_context(app.test_request_context(json={}))
    configuration = stack.enter_context(patch.object(action_service, "config"))
    configuration.api.external_sources = [plugin]
    stack.enter_context(patch.object(action_service, "get_supported_actions", return_value={"test_action": action}))
    stack.enter_context(patch.object(action_service, "get_obo_access_token", return_value=(None, None)))
    stack.enter_context(patch.object(action_service, "generate_headers", return_value={}))
    post = stack.enter_context(patch.object(action_service.requests, "post", return_value=responses[0]))
    get = stack.enter_context(patch.object(action_service.requests, "get", return_value=responses[1]))
    return stack, post, get


@pytest.mark.parametrize("task_id", LEGACY_TASK_IDS)
def test_pending_task_id_can_be_polled_to_completion(task_id):
    app = Flask(__name__)
    plugin = ExternalSource(name="test", url="http://plugin.internal:8080/api/")
    user = {"uname": "test-user", "classification": "TLP:CLEAR"}
    pending = MagicMock(status_code=200, ok=True)
    pending.json.return_value = {"api_response": {"outcome": "pending", "summary": "started", "task_id": task_id}}
    done = MagicMock(status_code=200, ok=True)
    done.json.return_value = {"api_response": {"outcome": "success", "format": "json", "output": []}}

    stack, _, get = _task_status_context(app, plugin, user, (pending, done))
    with stack:
        started = action_service.execute_action("test", "test_action", user)
        assert started.outcome == "pending"
        assert started.task_id == task_id

        assert action_service.get_action_status("test", "test_action", started.task_id, user).outcome == "success"

    url = get.call_args.args[0]
    expected = quote(task_id, safe="").replace(".", "%2E")
    assert url == f"http://plugin.internal:8080/api/actions/test_action/status/{expected}"
    parsed = urlsplit(url)
    assert (parsed.scheme, parsed.netloc) == ("http", "plugin.internal:8080")
    assert len(parsed.path.split("/")) == 6
    assert not parsed.query
    assert not parsed.fragment
    assert unquote(parsed.path.split("/")[-1]) == task_id


@pytest.mark.parametrize("task_id", BAD_TASK_IDS)
def test_status_rejects_unroutable_task_ids_before_any_upstream_call(task_id):
    app = Flask(__name__)
    plugin = ExternalSource(name="test", url="http://plugin.internal:8080/api/")
    user = {"uname": "test-user", "classification": "TLP:CLEAR"}
    response = MagicMock(status_code=200, ok=True)
    stack, post, get = _task_status_context(app, plugin, user, (response, response))
    with stack:
        with pytest.raises(ClueValueError) as error:
            action_service.get_action_status("test", "test_action", task_id, user)
    assert error.value.status_code == 400
    post.assert_not_called()
    get.assert_not_called()


@pytest.mark.parametrize("task_id", LEGACY_TASK_IDS)
def test_action_status_route_accepts_legacy_task_ids(task_id):
    from clue.api.v1.actions import actions_api

    app = Flask(__name__)
    app.testing = True
    app.register_blueprint(actions_api)
    auth_result = AuthResult(
        user=AuthUser(uname="test-user", classification="TLP:CLEAR"),
        privileges={Privilege.READ, Privilege.WRITE},
    )
    with (
        patch("clue.security.auth_service.bearer_auth", return_value=auth_result),
        patch.object(config.api, "audit", False),
        patch.object(config.ui, "replication", False),
        patch.object(
            action_service, "get_action_status", return_value=ActionResult(outcome="success", format="json", output=[])
        ) as service,
        app.test_client() as client,
    ):
        response = client.get(
            f"/api/v1/actions/test/test_action/status/{quote(task_id, safe='')}",
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 200
    assert service.call_args.args[2] == task_id


@pytest.mark.parametrize(
    "encoded",
    [".", "..", "%2E%2E", "..%2Fadmin%2Fkeys", "%2E%2E%2F%2E%2E%2Fetc%2Fpasswd", "a%2Fb", "x%0A", "x%00"],
)
def test_action_status_route_neutralizes_traversal_task_ids(encoded):
    from clue.api.v1.actions import actions_api

    app = Flask(__name__)
    app.testing = True
    app.register_blueprint(actions_api)
    auth_result = AuthResult(
        user=AuthUser(uname="test-user", classification="TLP:CLEAR"),
        privileges={Privilege.READ, Privilege.WRITE},
    )
    with (
        patch("clue.security.auth_service.bearer_auth", return_value=auth_result),
        patch.object(config.api, "audit", False),
        patch.object(config.ui, "replication", False),
        patch.object(action_service, "get_action_status") as service,
        app.test_client() as client,
    ):
        response = client.get(
            f"/api/v1/actions/test/test_action/status/{encoded}",
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code in {400, 404}
    service.assert_not_called()


@pytest.mark.parametrize("raise_on_error", [False, True])
@pytest.mark.parametrize(
    ("key", "identifier"),
    [
        ("test_action/../admin", "test_action"),
        ("test_action", "test_action/../admin"),
        ("test_action", "test..test_action"),
        ("test_action\n", "test_action"),
        ("test_action", ""),
        ("..", "test_action"),
    ],
)
def test_action_metadata_rejects_unsafe_identifiers(key, identifier, raise_on_error):
    plugin = ExternalSource(name="test", url="http://plugin/")
    response = MagicMock(status_code=200, ok=True)
    response.json.return_value = {
        "api_response": {
            key: {
                "id": identifier,
                "name": "Test",
                "classification": "TLP:CLEAR",
                "supported_types": ["ipv4"],
                "params": {},
            }
        }
    }
    with patch.object(action_service.requests, "get", return_value=response):
        if raise_on_error:
            with pytest.raises(ClueException, match="Unable to verify action availability") as error:
                action_service.get_supported_actions(plugin, {}, raise_on_error=True)
            assert error.value.status_code == 503
        else:
            assert action_service.get_supported_actions(plugin, {}) == {}


@pytest.mark.parametrize("identifier", ["Action_123-test", "test.action", "action.v2"])
@pytest.mark.parametrize("key", [None, "lookup_alias"])
@pytest.mark.parametrize("raise_on_error", [False, True])
def test_action_metadata_accepts_safe_ascii_identifiers(identifier, key, raise_on_error):
    key = identifier if key is None else key
    action = ActionSpec(
        id=identifier,
        name="Test",
        classification="TLP:CLEAR",
        supported_types={"ipv4"},
        params={},
    )
    response = MagicMock(status_code=200, ok=True)
    response.json.return_value = {"api_response": {key: action.model_dump()}}
    with patch.object(action_service.requests, "get", return_value=response):
        assert action_service.get_supported_actions(
            ExternalSource(name="test", url="http://plugin/"), {}, raise_on_error=raise_on_error
        ) == {key: action}


@pytest.mark.parametrize("operation", ["get_plugins_supported_actions", "execute_action", "get_action_status"])
@pytest.mark.parametrize("identifier", ["test.test_action", "other_action", "other.test_action"])
def test_action_metadata_preserves_local_lookup_key(operation, identifier):
    app = Flask(__name__)
    plugin = ExternalSource(name="test", url="http://plugin/")
    user = {"uname": "test-user", "classification": "TLP:CLEAR"}
    action = ActionSpec(id=identifier, name="Test", classification="TLP:CLEAR", supported_types={"ipv4"}, params={})
    metadata_response = MagicMock(status_code=200, ok=True)
    metadata_response.json.return_value = {"api_response": {"test_action": action.model_dump()}}
    result_response = MagicMock(status_code=200, ok=True)
    result_response.json.return_value = {"api_response": {"outcome": "success", "format": "json", "output": []}}
    with (
        app.test_request_context(json={}),
        patch.object(action_service, "config") as configuration,
        patch.object(action_service, "get_obo_access_token", return_value=(None, None)),
        patch.object(action_service, "generate_headers", return_value={}),
        patch.object(action_service.requests, "get", side_effect=[metadata_response, result_response]) as get,
        patch.object(action_service.requests, "post", return_value=result_response) as post,
    ):
        configuration.api.external_sources = [plugin]
        if operation == "get_plugins_supported_actions":
            result = action_service.get_plugins_supported_actions(user)
            assert set(result) == {"test.test_action"}
            assert result["test.test_action"].id == identifier
            post.assert_not_called()
        elif operation == "execute_action":
            assert action_service.execute_action("test", "test_action", user).outcome == "success"
            assert post.call_args.args[0] == "http://plugin/actions/test_action"
        else:
            assert action_service.get_action_status("test", "test_action", "task-123", user).outcome == "success"
            assert get.call_args.args[0] == "http://plugin/actions/test_action/status/task-123"
            post.assert_not_called()
    assert get.call_args_list[0].args[0] == "http://plugin/actions/"


@pytest.mark.parametrize(
    ("authorization", "expected_token"),
    [
        ("Bearer access-token", "access-token"),
        ("bearer access-token", "access-token"),
        ("opaque-token", "opaque-token"),
    ],
)
def test_action_obo_access_token_parses_authorization_header(authorization, expected_token):
    app = Flask(__name__)
    plugin = ExternalSource(name="test", url="http://plugin/")
    user = {"uname": "test-user"}

    with (
        app.test_request_context(headers={"Authorization": authorization}),
        patch("clue.helper.obo.auth_service.check_obo", return_value=("obo-token", None)) as check_obo,
    ):
        result = get_obo_access_token(plugin, user)

    assert result == (expected_token, "obo-token")
    check_obo.assert_called_once_with(plugin, expected_token, "test-user")


def test_action_obo_access_token_rejects_invalid_token():
    app = Flask(__name__)
    plugin = ExternalSource(name="test", url="http://plugin/")
    user = {"uname": "test-user"}

    with (
        app.test_request_context(headers={"Authorization": "Bearer access-token"}),
        patch("clue.helper.obo.auth_service.check_obo", return_value=(None, "invalid token")),
    ):
        with pytest.raises(AuthenticationException, match="Invalid token provided"):
            get_obo_access_token(plugin, user)


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
        patch("clue.helper.obo.auth_service.check_obo", return_value=("obo-token", None)) as check_obo,
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
        patch("clue.helper.obo.auth_service.check_obo", return_value=("obo-token", None)),
        patch(
            "clue.services.action_service.CLASSIFICATION.is_accessible",
            side_effect=lambda user_clearance, target: user_clearance == "TLP:AMBER" or target == "TLP:CLEAR",
        ),
    ):
        configuration.api.external_sources = [public_plugin, restricted_plugin]
        result = action_service.get_plugins_supported_actions(user)

    if clearance == "TLP:CLEAR":
        assert result == {"public.public_action": action}
        get_supported.assert_called_once_with(
            public_plugin,
            {
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": "Bearer obo-token",
                "X-Clue-Authorization": "access-token",
            },
        )
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
        patch("clue.helper.obo.auth_service.check_obo", return_value=("obo-token", None)) as check_obo,
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
    with (
        cached_app.app_context(),
        patch("clue.services.action_service.requests.get", return_value=metadata_response) as get,
    ):
        headers = {"accept": "application/json", "content-type": "application/json"}
        first = action_service.get_supported_actions(plugin, headers)
        assert action_service.get_supported_actions(plugin, headers) == first
        assert get.call_count == 2


@pytest.mark.parametrize("failure", ["timeout", "http_error", "invalid_metadata", "empty"])
def test_action_metadata_failures_are_not_cached(cached_app, metadata_response, failure):
    plugin = ExternalSource(name="test", url="http://plugin/")
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
        headers = {"accept": "application/json", "content-type": "application/json"}
        assert action_service.get_supported_actions(plugin, headers) == {}
        assert "test_action" in action_service.get_supported_actions(plugin, headers)
        assert get.call_count == 2


@pytest.mark.parametrize("failure", ["timeout", "http_error"])
def test_action_status_fails_closed_when_metadata_is_unavailable(cached_app, failure):
    plugin = ExternalSource(name="test", url="http://plugin/")
    user = {"uname": "test-user", "classification": "TLP:CLEAR"}
    failed_response = MagicMock()
    failed_response.ok = False
    failed_response.status_code = 503
    failed_response.json.return_value = {"api_error_message": "Unavailable"}
    get_metadata = (
        patch("clue.services.action_service.requests.get", side_effect=exceptions.Timeout())
        if failure == "timeout"
        else patch("clue.services.action_service.requests.get", return_value=failed_response)
    )

    with (
        cached_app.test_request_context(query_string={"max_timeout": "3.0"}),
        patch.object(action_service, "config") as configuration,
        patch("clue.services.action_service.CLASSIFICATION.is_accessible", return_value=True),
        get_metadata as get,
    ):
        configuration.api.external_sources = [plugin]
        with pytest.raises(ClueException, match="Unable to verify action availability") as error:
            action_service.get_action_status("test", "test_action", "task-123", user)

    assert error.value.status_code == 503
    get.assert_called_once_with(
        "http://plugin/actions/",
        headers={"accept": "application/json", "content-type": "application/json"},
        timeout=3.0,
        allow_redirects=False,
    )


def test_action_status_shares_timeout_budget_with_metadata(cached_app):
    plugin = ExternalSource(name="test", url="http://plugin/")
    user = {"uname": "test-user", "classification": "TLP:CLEAR"}
    action = ActionSpec(
        id="test_action", name="Test action", classification="TLP:CLEAR", supported_types={"ipv4"}, params={}
    )
    operation_response = MagicMock()
    operation_response.ok = True
    operation_response.json.return_value = {"api_response": {"outcome": "success", "format": "json", "output": []}}

    with (
        cached_app.test_request_context(query_string={"max_timeout": "12.5"}),
        patch.object(action_service, "config") as configuration,
        patch("clue.services.action_service.CLASSIFICATION.is_accessible", return_value=True),
        patch.object(action_service, "get_supported_actions", return_value={"test_action": action}) as get_supported,
        patch("clue.services.action_service.monotonic", side_effect=[0.0, 2.5]),
        patch("clue.services.action_service.requests.get", return_value=operation_response) as get,
    ):
        configuration.api.external_sources = [plugin]
        assert action_service.get_action_status("test", "test_action", "task-123", user).outcome == "success"

    get_supported.assert_called_once_with(
        plugin,
        {"accept": "application/json", "content-type": "application/json"},
        timeout=10.0,
        raise_on_error=True,
    )
    get.assert_called_once_with(
        "http://plugin/actions/test_action/status/task-123",
        headers={"accept": "application/json", "content-type": "application/json"},
        timeout=10.0,
        allow_redirects=False,
    )


@pytest.mark.parametrize("operation", ["execute_action", "get_action_status"])
def test_previous_action_metadata_does_not_bypass_obo_failure(cached_app, metadata_response, operation):
    plugin = ExternalSource(name="test", url="http://plugin/", classification="TLP:CLEAR")
    user = {"uname": "test-user", "classification": "TLP:CLEAR"}
    with (
        cached_app.test_request_context(json={}, headers={"Authorization": "Bearer access-token"}),
        patch.object(action_service, "config") as configuration,
        patch("clue.services.action_service.CLASSIFICATION.is_accessible", return_value=True),
        patch.object(action_service, "generate_headers", return_value={"Authorization": "Bearer obo-token"}),
        patch("clue.helper.obo.auth_service.check_obo", return_value=(None, "Invalid token")) as check_obo,
        patch("clue.services.action_service.requests.get", return_value=metadata_response) as get,
        patch("clue.services.action_service.requests.post") as post,
    ):
        configuration.api.external_sources = [plugin]
        assert "test_action" in action_service.get_supported_actions(plugin, {"Authorization": "Bearer obo-token"})
        if operation == "execute_action":
            result = action_service.execute_action("test", "test_action", user)
        else:
            result = action_service.get_action_status("test", "test_action", "task-123", user)
        assert result.outcome == "failure"
        check_obo.assert_called_once_with(plugin, "access-token", "test-user")
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
        patch("clue.helper.obo.auth_service.check_obo", return_value=("obo-token", None)) as check_obo,
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
        if operation == "get_action_status" and change in {"timeout", "http_error"}:
            with pytest.raises(ClueException, match="Unable to verify action availability") as error:
                getattr(action_service, operation)(*arguments)
            assert error.value.status_code == 503
        else:
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
