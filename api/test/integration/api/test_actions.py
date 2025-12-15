import pytest
import requests

from test.utils.oauth_credentials import get_token
from test.utils.test_server import Params


@pytest.fixture()
def access_token():
    return get_token()


def test_get_types(host, access_token):
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.get(
        f"{host}/api/v1/actions",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert "test.test_action" in response
    assert response["test.test_action"]["name"] == "Test Action"
    assert response["test.test_action"]["classification"] == "TLP:CLEAR"
    assert response["test.test_action"]["params"] == Params.model_json_schema()


def test_run_action(host, access_token):
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_action",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"selector": {"type": "ip", "value": "127.0.0.1"}, "other_choice": "b"},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["summary"] == "We got a value"
    assert response["output"]["value"]["value"] == "127.0.0.1"

    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_action",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"selector": {"type": "ip", "value": "127.0.0.1"}, "other_value": "test", "other_choice": "b"},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["summary"] == "We got a param value"
    assert response["output"]["value"] == "test"

    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_action",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "selector": {"type": "ip", "value": "127.0.0.1"},
            "other_value": "testerino",
            "other_choice": "a",
            "choice": "a",
        },
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["summary"] == "We got a param value"
    assert response["output"]["value"] == "testerino"


def test_run_action_multiple(host, access_token):
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_action",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "selectors": [{"type": "ip", "value": "127.0.0.1"}, {"type": "ip", "value": "127.0.0.2"}],
            "other_choice": "b",
        },
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["summary"] == "We got values"
    assert response["output"]["values"] == ["127.0.0.1", "127.0.0.2"]

    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_action",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "selectors": [{"type": "ip", "value": "127.0.0.1"}, {"type": "ip", "value": "127.0.0.2"}],
            "other_value": "test",
            "other_choice": "b",
        },
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["summary"] == "We got a param value"
    assert response["output"]["value"] == "test"

    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_action",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "selectors": [{"type": "ip", "value": "127.0.0.1"}, {"type": "ip", "value": "127.0.0.2"}],
            "other_value": "testerino",
            "other_choice": "a",
            "choice": "a",
        },
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["summary"] == "We got a param value"
    assert response["output"]["value"] == "testerino"


def test_run_action_empty(host, access_token):
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_action_empty",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"other_choice": "b"},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["summary"] == "We don't got a value"
    assert response["output"]["value"] is None

    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_action_empty",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"selector": {"type": "ip", "value": "127.0.0.1"}, "other_choice": "b"},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "failure"
    assert response["summary"] == "We got a value"
    assert response["output"]["value"]["value"] == "127.0.0.1"


def test_run_action_multiple_not_supported(host, access_token):
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_action_single",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "selectors": [{"type": "ip", "value": "127.0.0.1"}, {"type": "ip", "value": "127.0.0.2"}],
            "other_choice": "b",
        },
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "failure"
    assert response["summary"] == "We don't got a value"


def test_run_pivot(host, access_token):
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_pivot",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"selectors": [{"type": "ip", "value": "127.0.0.1"}, {"type": "ip", "value": "127.0.0.2"}]},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["output"] == "https://www.google.com/search?q=127.0.0.1+or+127.0.0.2"


def test_no_actions(host, access_token):
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/actions/execute/slow/test_action",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert not res.ok

    response = res.json()

    assert response["api_error_message"] == "slow_server does not support any actions."


def test_run_action_email(host, access_token):
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_action",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"selector": {"type": "eml_address", "value": "test"}, "other_choice": "b"},
    )

    assert res.ok

    response = res.json()

    assert "success" in response["api_response"]["outcome"]
    assert "email_address" in response["api_response"]["output"]["value"]["type"]

    assert response["api_response"]["summary"] == "We got a value"
    assert response["api_response"]["output"]["value"]["value"] == "test"


def test_run_action_multiple_email(host, access_token):
    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_action",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "selectors": [{"type": "eml_address", "value": "test"}, {"type": "ip", "value": "127.0.0.1"}],
            "other_value": "test",
            "other_choice": "b",
        },
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["summary"] == "We got a param value"
    assert response["output"]["value"] == "test"

    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_action",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "selectors": [{"type": "eml_address", "value": "test"}, {"type": "ip", "value": "127.0.0.1"}],
            "other_value": "testerino",
            "other_choice": "a",
            "choice": "a",
        },
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["summary"] == "We got a param value"
    assert response["output"]["value"] == "testerino"


def test_run_action_with_context(host, access_token):
    """Test that context is properly passed to actions"""
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    # Test with typed fields (url, timestamp, language) and arbitrary fields
    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_context",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "selector": {"type": "ip", "value": "127.0.0.1"},
            "context": {
                "url": "https://example.com/investigation/123",
                "timestamp": "2024-01-01T12:00:00Z",
                "language": "en",
                "source": "ui",
                "user_id": 123,
                "metadata": {"version": "1.0", "feature": "test"},
            },
        },
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["summary"] == "Context received"
    # Test typed fields are accessible
    assert response["output"]["url"] == "https://example.com/investigation/123"
    assert response["output"]["timestamp"] == "2024-01-01T12:00:00Z"
    assert response["output"]["language"] == "en"
    assert response["output"]["source"] == "ui"

    # Test arbitrary fields still work
    assert response["output"]["context"]["user_id"] == 123
    assert response["output"]["context"]["metadata"]["version"] == "1.0"
    assert response["output"]["context"]["metadata"]["feature"] == "test"
    assert "source" not in response["output"]["context"]

    # Test without context
    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_context",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"selector": {"type": "ip", "value": "127.0.0.1"}},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "failure"
    assert response["summary"] == "No context provided"
    assert response["output"]["context"] is None

    # Test with empty context
    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_context",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"selector": {"type": "ip", "value": "127.0.0.1"}, "context": {}},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["summary"] == "Context received"
    assert response["output"]["context"] == {}

    # Typed fields should be None when not provided
    assert response["output"]["url"] is None
    assert response["output"]["timestamp"] is None
    assert response["output"]["language"] is None

    # Test with only some typed fields provided
    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_context",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "selector": {"type": "ip", "value": "127.0.0.1"},
            "context": {
                "url": "https://example.com/case/456",
                "timestamp": "2024-12-12T10:30:00Z",
                # language not provided
                "custom_field": "custom_value",
            },
        },
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["output"]["url"] == "https://example.com/case/456"
    assert response["output"]["timestamp"] == "2024-12-12T10:30:00Z"
    assert response["output"]["language"] is None
    assert response["output"]["context"]["custom_field"] == "custom_value"

    # Test context with various data types
    res = requests.post(
        f"{host}/api/v1/actions/execute/test/test_context",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "selector": {"type": "ip", "value": "127.0.0.1"},
            "context": {
                "language": None,  # Test explicit None for typed field
                "string_field": "test_string",
                "int_field": 42,
                "float_field": 3.14,
                "bool_field": True,
                "list_field": [1, 2, 3],
                "null_field": None,
                "nested": {"key": "value"},
            },
        },
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["output"]["language"] is None
    assert response["output"]["context"]["string_field"] == "test_string"
    assert response["output"]["context"]["int_field"] == 42
    assert response["output"]["context"]["float_field"] == 3.14
    assert response["output"]["context"]["bool_field"] is True
    assert response["output"]["context"]["list_field"] == [1, 2, 3]
    assert response["output"]["context"]["null_field"] is None
    assert response["output"]["context"]["nested"]["key"] == "value"
