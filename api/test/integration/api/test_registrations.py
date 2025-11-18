from typing import Any

import pytest
import requests

from clue.api.v1.registration import EXTERNAL_PLUGIN_SET
from clue.models.config import ExternalSource
from test.utils.oauth_credentials import get_token


def test_registration(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    sample_plugin = {
        "name": "test",
        "classification": "TLP:CLEAR",
        "max_classification": "TLP:CLEAR",
        "url": "http://localhost:5008/",
        "maintainer": "Example <example@example.com>",
        "datahub_link": "http://example.com",
        "documentation_link": "http://example.com",
        "type": "ip",
        "value": "127.0.0.1",
    }

    res = requests.post(
        f"{host}/api/v1/registration/register/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=sample_plugin,
    )
    assert res.ok
    assert (ExternalSource(**sample_plugin, built_in=False)).model_dump(
        mode="json", exclude_none=True
    ) in EXTERNAL_PLUGIN_SET.members()


def test_registration_incorrect_json(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    sample_plugin = {
        "name": "test",
        "classification": "TLP:CLEAR",
        "max_classification": "TLP:CLEAR",
        "maintainer": "Example <example@example.com>",
        "datahub_link": "http://example.com",
        "documentation_link": "http://example.com",
        "type": "ip",
        "value": "127.0.0.1",
    }

    res = requests.post(
        f"{host}/api/v1/registration/register",
        headers={"Authorization": f"Bearer {access_token}"},
        json=sample_plugin,
    )
    assert not res.ok


def test_registration_no_data_provided(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    sample_plugin = ""

    res = requests.post(
        f"{host}/api/v1/registration/register/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=sample_plugin,
    )
    assert not res.ok


def test_registration_no_data_json_provided(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/registration/register/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=None,
    )
    assert not res.ok


def test_get_enrichment_from_new_plugin(host):
    access_token = get_token()

    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    sample_plugin = {
        "name": "test_enrich",
        "classification": "TLP:CLEAR",
        "max_classification": "TLP:CLEAR",
        "url": "http://localhost:5008/",
        "maintainer": "Example <example@example.com>",
        "datahub_link": "http://example.com",
        "documentation_link": "http://example.com",
        "type": "ip",
        "value": "127.0.0.1",
    }

    res = requests.post(
        f"{host}/api/v1/registration/register/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=sample_plugin,
    )

    enrich_res = requests.get(
        f"{host}/api/v1/lookup/enrich/ipv4/127.0.0.1/?sources=test_enrich",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    json: dict[str, dict[str, Any]] = enrich_res.json()["api_response"]
    assert "error" not in json["test_enrich"]
    assert json["test_enrich"]["maintainer"] == "Example <example@example.com>"
    assert json["test_enrich"]["datahub_link"] == "http://example.com/"
    assert json["test_enrich"]["documentation_link"] == "http://example.com/"

    assert json["test_enrich"]["items"][0]["count"] == 10
    assert json["test_enrich"]["items"][0]["link"] == "https://example.com/"

    assert res.ok
    assert enrich_res.ok


def test_remove_application(host):
    access_token = get_token()
    if not access_token:
        pytest.skip("Could not connect to keycloak - is keycloak running?")

    sample_plugin = {
        "name": "test",
        "classification": "TLP:CLEAR",
        "max_classification": "TLP:CLEAR",
        "url": "http://localhost:5008/",
        "maintainer": "Example <example@example.com>",
        "datahub_link": "http://example.com",
        "documentation_link": "http://example.com",
        "type": "ip",
        "value": "127.0.0.1",
    }

    res = requests.post(
        f"{host}/api/v1/registration/register/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=sample_plugin,
    )

    res = requests.delete(f"{host}/api/v1/registration/test", headers={"Authorization": f"Bearer {access_token}"})

    assert res.ok
    assert (ExternalSource(**sample_plugin, built_in=False)).model_dump(
        mode="json", exclude_none=True
    ) not in EXTERNAL_PLUGIN_SET.members()


def test_remove_application_when_no_plugin_found(host):
    access_token = get_token()
    list_length = len(EXTERNAL_PLUGIN_SET.members())

    if not access_token:
        pytest.skip("Could not connect to keycloak - is keycloak running?")

    plugin_id = "Null"
    res = requests.delete(
        f"{host}/api/v1/registration/{plugin_id}", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert res.status_code == 204
    assert len(EXTERNAL_PLUGIN_SET.members()) == list_length
