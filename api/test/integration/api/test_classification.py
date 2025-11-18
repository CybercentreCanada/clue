from typing import Any

import pytest
import requests

from test.utils.oauth_credentials import get_token


def test_get_enrichment(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.get(
        f"{host}/api/v1/lookup/enrich/ipv4/127.0.0.1",
        params={"max_timeout": 2.0, "classification": "TLP:AMBER+STRICT", "sources": "test|test-amber"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert res.ok

    json: dict[str, dict[str, Any]] = res.json()["api_response"]

    assert json["test"]["error"] == "Type classification exceeds max classification of source: test."
    assert "error" not in json["test-amber"]
