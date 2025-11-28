from datetime import datetime
from typing import Any

import pytest
import requests

from test.utils.oauth_credentials import get_token


def test_get_types(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.get(
        f"{host}/api/v1/lookup/types",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert res.ok
    assert sorted(res.json()["api_response"]["test"]) == sorted(["ipv4", "ipv6", "port", "sha256"])


def test_get_enrichment(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.get(
        f"{host}/api/v1/lookup/enrich/ipv4/127.0.0.1",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert res.ok

    json: dict[str, dict[str, Any]] = res.json()["api_response"]

    assert "error" not in json["test"]
    assert json["bad"]["error"]

    assert json["test"]["maintainer"] == "Example <example@example.com>"
    assert json["test"]["datahub_link"] == "http://example.com/"
    assert json["test"]["documentation_link"] == "http://example.com/"

    assert json["test"]["items"][0]["count"] == 10
    assert json["test"]["items"][0]["link"] == "https://example.com/"

    assert json["test"]["items"][0]["annotations"][0] == {
        "analytic": "test enrichment",
        "type": "opinion",
        "value": "malicious",
        "confidence": 0.7,
        "severity": 1.0,
        "priority": 0.7,
        "summary": "This is a bad ip",
        "details": "# Breaking news\nThis is a bad IP",
        "quantity": 1,
        "timestamp": datetime(2024, 1, 1, 1, 1, 1).isoformat(),
        "version": "0.0.1",
        "ubiquitous": False,
    }

    assert json["test"]["items"][0]["raw_data"][0] == {"classification": "TLP:CLEAR", "data": '{"test": "raw data"}'}
    assert '"count": Input should be a valid integer' in json["bad"]["error"]
    assert '"annotations.[0].type": Field required' in json["bad"]["error"]
    assert '"annotations.[0].value": Field required' in json["bad"]["error"]
    assert '"annotations.[0].summary": Field required' in json["bad"]["error"]


def test_separators(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.get(
        f"{host}/api/v1/lookup/enrich/ipv4/127.0.0.1",
        params={"max_timeout": 2.0, "classification": "TLP:CLEAR", "sources": "test|test-amber"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert res.ok

    json: dict[str, dict[str, Any]] = res.json()["api_response"]

    assert "error" not in json["test"]
    assert "error" not in json["test-amber"]

    res = requests.get(
        f"{host}/api/v1/lookup/enrich/ipv4/127.0.0.1",
        params={"max_timeout": 2.0, "classification": "TLP:CLEAR", "sources": "test,test-amber"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert res.ok

    json: dict[str, dict[str, Any]] = res.json()["api_response"]

    assert "error" not in json["test"]
    assert "error" not in json["test-amber"]


def test_bulk_enrichment(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    bulk_req = [{"type": "ipv4", "value": "127.0.0.1"}, {"type": "ipv6", "value": "127.0.0.2"}]

    res = requests.post(
        f"{host}/api/v1/lookup/enrich",
        params={"max_timeout": 5.0, "sources": "test|bad"},
        headers={"Authorization": f"Bearer {access_token}"},
        json=bulk_req,
    )

    assert res.ok

    json: dict[str, dict[str, Any]] = res.json()["api_response"]

    for entry in bulk_req:
        assert (
            "error" not in json[entry["type"]][entry["value"]]["test"]
            or not json[entry["type"]][entry["value"]]["test"]["error"]
        )
        assert json[entry["type"]][entry["value"]]["bad"]["error"]

        assert json[entry["type"]][entry["value"]]["test"]["items"][0]["count"] == 10
        assert json[entry["type"]][entry["value"]]["test"]["items"][0]["link"] == "https://example.com/"

        assert json[entry["type"]][entry["value"]]["test"]["items"][0]["annotations"][0] == {
            "analytic": "test enrichment",
            "type": "opinion",
            "value": "malicious",
            "confidence": 0.7,
            "severity": 1.0,
            "priority": 0.7,
            "summary": "This is a bad ip",
            "details": "# Breaking news\nThis is a bad IP",
            "quantity": 1,
            "timestamp": datetime(2024, 1, 1, 1, 1, 1).isoformat(),
            "version": "0.0.1",
            "ubiquitous": False,
        }

        assert json[entry["type"]][entry["value"]]["test"]["items"][0]["raw_data"][0] == {
            "classification": "TLP:CLEAR",
            "data": '{"test": "raw data"}',
        }

        assert (
            '"items.[0].count": Input should be a valid integer' in json[entry["type"]][entry["value"]]["bad"]["error"]
        )
        assert '"items.[0].annotations.[0].type": Field required' in json[entry["type"]][entry["value"]]["bad"]["error"]
        assert (
            '"items.[0].annotations.[0].value": Field required' in json[entry["type"]][entry["value"]]["bad"]["error"]
        )
        assert (
            '"items.[0].annotations.[0].summary": Field required' in json[entry["type"]][entry["value"]]["bad"]["error"]
        )


def test_bulk_enrichment_ip_entry(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    bulk_req = [
        {"type": "ip", "value": "127.0.0.1"},
        {"type": "ip", "value": "2001:0db8:85a3:0000:0000:8a2e:0370:7339"},
    ]

    res = requests.post(
        f"{host}/api/v1/lookup/enrich",
        params={"max_timeout": 5.0, "sources": "test|bad"},
        headers={"Authorization": f"Bearer {access_token}"},
        json=bulk_req,
    )

    assert res.ok
    assert "ipv4" in res.json()["api_response"] and "ipv6" in res.json()["api_response"]


def test_bulk_wrong(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/lookup/enrich",
        params={"max_timeout": 2.0, "sources": "test|bad"},
        headers={"Authorization": f"Bearer {access_token}"},
        json={},
    )

    assert not res.ok
    assert "Request data is not in the correct format" in res.json()["api_error_message"]

    res = requests.post(
        f"{host}/api/v1/lookup/enrich",
        params={"max_timeout": 2.0, "sources": "test|bad"},
        headers={"Authorization": f"Bearer {access_token}"},
        json=[{"banana": "test"}],
    )

    assert not res.ok
    assert "Request data is not in the correct format" in res.json()["api_error_message"]

    res = requests.post(
        f"{host}/api/v1/lookup/enrich",
        params={"max_timeout": 2.0, "sources": "test"},
        headers={"Authorization": f"Bearer {access_token}"},
        json=[],
    )

    assert not res.ok
    assert "You must provide at least one value to lookup" in res.json()["api_error_message"]


def test_bulk_enrichment_eml_correction(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    bulk_req = [{"type": "eml_address", "value": "test@123.com"}, {"type": "ip", "value": "127.0.0.2"}]

    res = requests.post(
        f"{host}/api/v1/lookup/enrich",
        params={"max_timeout": 5.0, "sources": "test|bad"},
        headers={"Authorization": f"Bearer {access_token}"},
        json=bulk_req,
    )

    assert res.ok

    assert "email_address" in res.json()["api_response"]


def test_get_enrichment_eml(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.get(
        f"{host}/api/v1/lookup/enrich/eml_address/test@123.com",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert res.ok


def test_bulk_enrichment_sources(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    bulk_req: list[dict[str, Any]] = [
        {"type": "ipv4", "value": "127.0.0.1", "sources": ["test", "bad"]},
        {"type": "ipv4", "value": "127.0.0.2", "sources": ["test-amber"]},
    ]

    res = requests.post(
        f"{host}/api/v1/lookup/enrich",
        params={"max_timeout": 5.0},
        headers={"Authorization": f"Bearer {access_token}"},
        json=bulk_req,
    )

    assert res.ok

    json: dict[str, dict[str, Any]] = res.json()["api_response"]

    for entry in bulk_req:
        if "bad" in entry["sources"]:
            assert json[entry["type"]][entry["value"]]["bad"]["error"]
        else:
            assert "bad" not in json[entry["type"]][entry["value"]]

        if "test" in entry["sources"]:
            assert "error" not in json[entry["type"]][entry["value"]]["test"]
        else:
            assert "test" not in json[entry["type"]][entry["value"]]

        if "test-amber" in entry["sources"]:
            assert "error" not in json[entry["type"]][entry["value"]]["test-amber"]
        else:
            assert "test-amber" not in json[entry["type"]][entry["value"]]


def test_case_normalization_single(host):
    """Test that type and value are normalized to lowercase for single enrichment."""
    access_token = get_token()
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    # Mixed case type and value
    res = requests.get(
        f"{host}/api/v1/lookup/enrich/IPv4/127.0.0.1",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert res.ok
    json = res.json()["api_response"]

    # Should respond as if type/value were lowercase
    assert "test" in json
    assert json["test"]["items"][0]["count"] == 10

    # Uppercase value
    res = requests.get(
        f"{host}/api/v1/lookup/enrich/IPV4/127.0.0.1",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert res.ok
    json = res.json()["api_response"]

    assert "test" in json
    assert json["test"]["items"][0]["count"] == 10


def test_case_normalization_bulk(host):
    """Test that type and value are normalized to lowercase for bulk enrichment."""
    access_token = get_token()
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    bulk_req = [
        {"type": "IPv4", "value": "127.0.0.1"},
        {"type": "IPV6", "value": "127.0.0.2"},
        {"type": "EmAiL_Address", "value": "TEST@123.COM"},
    ]
    res = requests.post(
        f"{host}/api/v1/lookup/enrich",
        params={"max_timeout": 5.0, "sources": "test|bad"},
        headers={"Authorization": f"Bearer {access_token}"},
        json=bulk_req,
    )
    assert res.ok
    json = res.json()["api_response"]
    # Should respond as if type/value were lowercase
    assert "ipv4" in json and "ipv6" in json and "email_address" in json
    assert json["ipv4"]["127.0.0.1"]["test"]["items"][0]["count"] == 10
    assert json["ipv6"]["127.0.0.2"]["test"]["items"][0]["count"] == 10
