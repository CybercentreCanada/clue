from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from clue.common.exceptions import NotFoundException
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
        patch.object(action_service.auth_service, "check_obo", return_value=("obo-token", None)) as check_obo,
        patch.object(action_service, "generate_headers", return_value={"Authorization": "Bearer obo-token"}),
        patch.object(
            action_service.CLASSIFICATION,
            "is_accessible",
            side_effect=lambda clearance, target: clearance == "TLP:AMBER" or target == "TLP:CLEAR",
        ) as is_accessible,
        patch.object(action_service.requests, "post", return_value=response) as post,
        patch.object(action_service.requests, "get", return_value=response) as get,
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
