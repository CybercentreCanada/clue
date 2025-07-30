import os
from copy import deepcopy

import pytest
import requests

from clue.models.graph import VisualConfig
from clue.models.results.status import StatusLabel, StatusResult
from test.utils.oauth_credentials import get_token
from test.utils.test_server import PROCESS_TREE


@pytest.fixture(scope="module")
def access_token():
    return get_token()


@pytest.fixture(scope="module")
def process_tree():
    tree = deepcopy(PROCESS_TREE)

    for col in tree["data"]:
        for row in col:
            if "icons" not in row:
                row["icons"] = []

    tree["metadata"]["display"]["visualization"]["config"] = {
        **VisualConfig().model_dump(mode="json", by_alias=True, exclude_none=True),
        **tree["metadata"]["display"]["visualization"]["config"],
    }

    return tree


def test_get_types(host, access_token):
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.get(
        f"{host}/api/v1/fetchers",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert "test.json" in response
    assert response["test.json"]["classification"] == os.environ.get("CLASSIFICATION", "TLP:CLEAR")
    assert response["test.json"]["description"] == "test fetcher json"
    assert response["test.json"]["format"] == "json"

    assert "test.image" in response
    assert response["test.image"]["classification"] == os.environ.get("CLASSIFICATION", "TLP:CLEAR")
    assert response["test.image"]["description"] == "test fetcher image"
    assert response["test.image"]["format"] == "image"

    assert "test.graph" in response
    assert response["test.graph"]["classification"] == os.environ.get("CLASSIFICATION", "TLP:CLEAR")
    assert response["test.graph"]["description"] == "test fetcher graph"
    assert response["test.graph"]["format"] == "graph"


def test_run_fetcher(host, access_token, process_tree):
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/fetchers/test/json",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"type": "ip", "value": "127.0.0.1"},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["data"] == {"potato": "test"}

    res = requests.post(
        f"{host}/api/v1/fetchers/test/image",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"type": "ip", "value": "127.0.0.1"},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["data"].get("image", None) is not None

    res = requests.post(
        f"{host}/api/v1/fetchers/test/graph",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"type": "ip", "value": "127.0.0.1"},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["data"] == process_tree

    # status
    res = requests.post(
        f"{host}/api/v1/fetchers/test/status",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"type": "ip", "value": "127.0.0.1"},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["data"] == StatusResult(
        labels=[
            StatusLabel(language="en", label="Status Label"),
            StatusLabel(language="fr", label="La Status Label"),
        ],
        color="#f542f2",
    ).model_dump(mode="json", exclude_none=True)


def test_no_fetchers(host, access_token):
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/fetchers/slow/json",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"type": "ip", "value": "127.0.0.1"},
    )

    assert not res.ok

    response = res.json()

    assert response["api_error_message"] == "slow_server does not support any fetchers."

    res = requests.post(
        f"{host}/api/v1/fetchers/test/json_missing_though",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"type": "ip", "value": "127.0.0.1"},
    )

    assert not res.ok

    response = res.json()

    assert response["api_error_message"] == "Fetcher json_missing_though does not exist"


def test_invalid_input(host, access_token):
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/fetchers/test/json",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert res.status_code == 400

    assert (
        res.json()["api_error_message"]
        == "Validation error encountered on request body. Ensure your request body is properly formatted."
    )

    res = requests.post(
        f"{host}/api/v1/fetchers/test/json",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"bogus": "dict"},
    )

    assert res.status_code == 400

    assert res.json()["api_error_message"].startswith("Validation error encountered on request body")


def test_invalid_input_direct(access_token):
    from clue.config import config

    test_source = next(source for source in config.api.external_sources if source.name == "test")

    res = requests.post(
        f"{test_source.url}/fetchers/json",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"bogus": "dict"},
    )

    assert res.status_code == 400
    assert res.json()["api_response"]["outcome"] == "failure"
    assert "validation error" in res.json()["api_response"]["error"]


def test_run_fetcher_email(host, access_token, process_tree):
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/fetchers/test/json",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"type": "eml_address", "value": "test"},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["data"] == {"potato": "test"}

    res = requests.post(
        f"{host}/api/v1/fetchers/test/image",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"type": "eml_address", "value": "test"},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["data"].get("image", None) is not None

    res = requests.post(
        f"{host}/api/v1/fetchers/test/graph",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"type": "eml_address", "value": "test"},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["data"] == process_tree

    # status
    res = requests.post(
        f"{host}/api/v1/fetchers/test/status",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"type": "eml_address", "value": "test"},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["outcome"] == "success"
    assert response["data"] == StatusResult(
        labels=[
            StatusLabel(language="en", label="Status Label"),
            StatusLabel(language="fr", label="La Status Label"),
        ],
        color="#f542f2",
    ).model_dump(mode="json", exclude_none=True)
