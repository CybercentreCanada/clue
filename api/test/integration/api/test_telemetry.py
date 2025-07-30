import json
import urllib.parse
from datetime import datetime

import pytest
import requests

from test.utils.oauth_credentials import get_token

TELEMETRY_JSON = json.dumps({"key1": "test", "timestamp": datetime.now().isoformat()})


def test_get_enrichment(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.get(
        f"{host}/api/v1/lookup/enrich/telemetry/{urllib.parse.quote(urllib.parse.quote(TELEMETRY_JSON))}",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert res.ok


def test_get_enrichment_wrong(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.get(
        f"{host}/api/v1/lookup/enrich/telemetry/potato",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert not res.ok
    assert "valid JSON" in res.json()["api_error_message"]


def test_bulk_enrichment(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    bulk_req = [
        {"type": "telemetry", "value": TELEMETRY_JSON},
        {"type": "telemetry", "value": TELEMETRY_JSON},
    ]

    res = requests.post(
        f"{host}/api/v1/lookup/enrich",
        params={"max_timeout": 5.0, "sources": "telemetry"},
        headers={"Authorization": f"Bearer {access_token}"},
        json=bulk_req,
    )

    assert res.ok


def test_bulk_wrong(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/lookup/enrich",
        params={"max_timeout": 2.0, "sources": "telemetry"},
        headers={"Authorization": f"Bearer {access_token}"},
        json={},
    )

    assert not res.ok
    assert "Request data is not in the correct format" in res.json()["api_error_message"]

    res = requests.post(
        f"{host}/api/v1/lookup/enrich",
        params={"max_timeout": 2.0, "sources": "telemetry"},
        headers={"Authorization": f"Bearer {access_token}"},
        json=[{"banana": "test"}],
    )

    assert not res.ok
    assert "Request data is not in the correct format" in res.json()["api_error_message"]

    res = requests.post(
        f"{host}/api/v1/lookup/enrich",
        params={"max_timeout": 2.0, "sources": "telemetry"},
        headers={"Authorization": f"Bearer {access_token}"},
        json=[],
    )

    assert not res.ok
    assert "You must provide at least one value to lookup" in res.json()["api_error_message"]

    bulk_req = [{"type": "telemetry", "value": "potato"}, {"type": "telemetry", "value": TELEMETRY_JSON}]

    res = requests.post(
        f"{host}/api/v1/lookup/enrich",
        params={"max_timeout": 2.0, "sources": "telemetry"},
        headers={"Authorization": f"Bearer {access_token}"},
        json=bulk_req,
    )

    assert not res.ok
    assert "valid JSON" in res.json()["api_error_message"]


def test_run_action(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/actions/execute/telemetry/retain",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "selectors": [
                {"type": "telemetry", "value": TELEMETRY_JSON},
                {"type": "telemetry", "value": TELEMETRY_JSON},
            ]
        },
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["output"]["value"] == json.loads(TELEMETRY_JSON)["timestamp"]


def test_run_action_single(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/actions/execute/telemetry/retain",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json={"selector": {"type": "telemetry", "value": TELEMETRY_JSON}},
    )

    assert res.ok

    response = res.json()["api_response"]

    assert response["output"]["value"] == json.loads(TELEMETRY_JSON)["timestamp"]
