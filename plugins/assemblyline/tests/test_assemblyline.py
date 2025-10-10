import datetime
from unittest.mock import ANY
from urllib import parse as ul

import pytest


def dquote(value):
    """Double encode the value."""
    return ul.quote(ul.quote(value, safe=""), safe="")


class FakeSearch:
    def __init__(self, responses, load_groups=True) -> None:
        self.alert_resp = responses["alert"]
        self.result_resp = responses["result"]
        self.safelist_resp = responses["safelist"]
        self.badlist_resp = responses["badlist"]
        self.file_resp = responses["file"]
        if load_groups:
            self.grouped = FakeSearch(responses, False)

    def alert(self, *args, **kwargs):
        return self.alert_resp

    def result(self, *args, **kwargs):
        return self.result_resp

    def safelist(self, *args, **kwargs):
        return self.safelist_resp

    def badlist(self, *args, **kwargs):
        return self.badlist_resp

    def file(self, *args, **kwargs):
        return self.file_resp


class FakeUser:
    def __init__(self, responses):
        self.submission_params_resp = responses["submission_params"]

    def submission_params(self, *args, **kwargs):
        return self.submission_params_resp


class FakeClient:
    empty_reponse = {
        "items": [],
        "offset": 0,
        "rows": 25,
        "total": 0,
    }

    def __init__(self) -> None:
        self.current_user = "testing-user"

        self.responses = {
            "alert": self.empty_reponse,
            "result": {
                "items": [
                    {
                        "value": "ConfigExtractor",
                        "items": [
                            {
                                "classification": "TLP:CLEAR",
                                "id": f"{'a' * 64}.service.version.id",
                                "result": {"score": 1000, "sections": []},
                                "response": {
                                    "service_name": "ConfigExtractor",
                                    "service_version": "4.5.0.dev0",
                                    "service_tool_version": "1b095b7",
                                },
                                "type": "executable/windows/pe32",
                            }
                        ],
                    }
                ],
                "offset": 0,
                "rows": 25,
                "total": 1,
            },
            "safelist": {
                "added": datetime.datetime.now().isoformat(),
                "attribution": {
                    "actor": None,
                    "campaign": None,
                    "category": None,
                    "exploit": None,
                    "family": ["BADGUY"],
                    "implant": None,
                    "network": None,
                },
                "classification": "TLP:CLEAR",
                "enabled": True,
                "expiry_ts": None,
                "file": None,
                "hashes": {
                    "md5": None,
                    "sha1": None,
                    "sha256": "a" * 32,
                    "ssdeep": None,
                    "tlsh": None,
                },
                "sources": [
                    {
                        "classification": "TLP:CLEAR",
                        "name": "urlhaus",
                        "reason": [
                            "IOC was reported by source as not malicious",
                            "https://example.com/",
                        ],
                        "type": "external",
                    }
                ],
                "tag": {"type": "network.static.uri", "value": "http://example.com"},
                "type": "tag",
                "updated": datetime.datetime.now().isoformat(),
            },
            "badlist": {
                "added": datetime.datetime.now().isoformat(),
                "attribution": {
                    "actor": None,
                    "campaign": None,
                    "category": None,
                    "exploit": None,
                    "family": ["BADGUY"],
                    "implant": None,
                    "network": None,
                },
                "classification": "TLP:CLEAR",
                "enabled": True,
                "expiry_ts": None,
                "file": None,
                "hashes": {
                    "md5": None,
                    "sha1": None,
                    "sha256": "a" * 32,
                    "ssdeep": None,
                    "tlsh": None,
                },
                "sources": [
                    {
                        "classification": "TLP:CLEAR",
                        "name": "urlhaus",
                        "reason": [
                            "IOC was reported by source as malicious",
                            "https://example.com/",
                        ],
                        "type": "external",
                    }
                ],
                "tag": {"type": "network.static.uri", "value": "http://example.com"},
                "type": "tag",
                "updated": datetime.datetime.now().isoformat(),
            },
            "file": self.empty_reponse,
            "submission_params": {
                "classification": "some default",
                "description": "",
                "submitter": "possibly-wrong",
                "services": {"selected": ["Cool Analysis"]},
            },
            "submit": {"sid": "some-sid"},
        }
        self.search = FakeSearch(self.responses)
        self.user = FakeUser(self.responses)

    def set_obo_token(*args, **kwargs):
        pass

    def clear_obo_token(*args, **kwargs):
        pass

    def set_response(self, type, val):
        self.responses[type] = val
        self.search = FakeSearch(self.responses)

    def alert(self, *args, **kwargs):
        return self.search.alert_resp

    def result(self, *args, **kwargs):
        return self.search.result_resp

    def safelist(self, *args, **kwargs):
        return self.search.safelist_resp

    def badlist(self, *args, **kwargs):
        return self.search.badlist_resp

    def submit(self, *args, **kwargs):
        return self.responses["submit"]


class FakeC12NEngine:
    UNRESTRICTED = "TLP:CLEAR"

    def max_classification(*args, **kwargs):
        return "TLP:CLEAR"


@pytest.fixture()
def al_client():
    yield FakeClient()


@pytest.fixture()
def al_c12n_engine():
    yield FakeC12NEngine()


@pytest.fixture()
def server(al_client, al_c12n_engine):
    from assemblyline import app

    orig = app.AL_API_KEY
    orig_client = app.CLIENT
    orig_c12n_engine = app.C12N_ENGINE
    app.CLIENT = al_client
    app.C12N_ENGINE = al_c12n_engine
    app.AL_API_KEY = "X"

    yield app

    server.AL_API_KEY = orig  # type: ignore[attr-defined]
    server.CLIENT = orig_client  # type: ignore[attr-defined]
    server.C12N_ENGINE = orig_c12n_engine  # type: ignore[attr-defined]


@pytest.fixture()
def test_client(server):
    """generate a test client."""
    with server.app.test_client() as client:
        with server.app.app_context():
            server.app.config["TESTING"] = True
            yield client


def test_get_mappings(test_client, server):
    """Ensure types are returned."""
    rsp = test_client.get("/types/")
    assert rsp.status_code == 200
    data = rsp.json["api_response"]
    assert data == {tname: server.CLASSIFICATION for tname in sorted(server.TYPE_MAPPING)}


def test_hash_found(test_client, al_client, server):
    """Validate respone for a hash that exists."""
    data = al_client.responses["result"]
    digest = data["items"][0]["items"][0]["id"].split(".", 1)[0]

    # sha256 can use the result index
    rsp = test_client.get(f"/lookup/sha256/{dquote(digest)}/", query_string={"no_annotation": True})
    expected = {
        "api_error_message": "",
        "api_response": [
            {
                "classification": "TLP:CLEAR",
                "count": 1,
                "annotations": [],
            },
            {
                "classification": "TLP:CLEAR",
                "link": f"{server.AL_URL_BASE}/manage/safelist/{digest}",
                "count": 1,
                "annotations": [],
            },
            {
                "classification": "TLP:CLEAR",
                "link": f"{server.AL_URL_BASE}/manage/badlist/{digest}",
                "count": 1,
                "annotations": [],
            },
        ],
        "api_status_code": 200,
    }

    assert rsp.status_code == 200, rsp.json["api_error_message"]
    assert rsp.json == expected


def test_hash_dne(test_client, al_client):
    """Validate response for a hash that does not exist."""
    al_client.set_response("file", al_client.empty_reponse)

    rsp = test_client.get(f"/lookup/md5/{dquote('a' * 32)}/", query_string={"no_annotation": True})
    expected = {
        "api_error_message": "",
        "api_response": [],
        "api_status_code": 404,
    }
    assert rsp.status_code == 404
    assert rsp.json == expected

    # invalid hashes will not raise an error and will just not be found
    rsp = test_client.get("/lookup/md5/abc}/", query_string={"no_annotation": True})
    expected = {
        "api_error_message": "",
        "api_response": [],
        "api_status_code": 404,
    }
    assert rsp.status_code == 404
    assert rsp.json == expected


def test_error_conditions(test_client, al_client):
    """Validate error handling."""
    al_client.set_response("file", "invalid response!")

    rsp = test_client.get(f"/lookup/md5/{dquote('a' * 32)}/")
    assert rsp.status_code == 500

    # invalid indicator name
    rsp = test_client.get("/lookup/abc/abc}/")
    assert rsp.status_code == 422
    assert rsp.json["api_error_message"].startswith("Invalid type name: ")


def test_detailed(test_client, server):
    """Test getting details for a valid type that is found and is malicious."""
    url = "https://a.bad.url/contains+and/a space/in-path"
    rsp = test_client.get(f"/lookup/url/{dquote(url)}/")
    expected = {
        "api_error_message": "",
        "api_response": [
            {
                "classification": "TLP:CLEAR",
                "count": 1,
                "annotations": [],
            },
            {
                "classification": "TLP:CLEAR",
                "link": f"{server.AL_URL_BASE}/manage/safelist/9cffecf270e3553f45f5d702c204883d01"
                "906d91c1d22dfa5d56868abcd7ff2c",
                "count": 1,
                "annotations": [
                    {
                        "analytic": "Assemblyline - Safelist",
                        "confidence": 1.0,
                        "link": "https://assemblyline-ui/manage/safelist/9cffecf270e3553f45f5d702c204883"
                        "d01906d91c1d22dfa5d56868abcd7ff2c",
                        "quantity": 1,
                        "summary": "Assemblyline's safelist flagged this URI as benign in 1 "
                        "source(s): urlhaus (external)",
                        "timestamp": ANY,
                        "type": "opinion",
                        "ubiquitous": False,
                        "value": "benign",
                    }
                ],
            },
            {
                "classification": "TLP:CLEAR",
                "link": f"{server.AL_URL_BASE}/manage/badlist/9cffecf270e3553f45f5d702c204883d01906d91"
                "c1d22dfa5d56868abcd7ff2c",
                "count": 1,
                "annotations": [
                    {
                        "analytic": "Assemblyline - Badlist",
                        "confidence": 1.0,
                        "link": "https://assemblyline-ui/manage/badlist/9cffecf270e3553f45f5d702c204883d0190"
                        "6d91c1d22dfa5d56868abcd7ff2c",
                        "quantity": 1,
                        "summary": "Assemblyline's badlist flagged this URI as malicious in 1 "
                        "source(s): urlhaus (external)",
                        "timestamp": ANY,
                        "type": "opinion",
                        "ubiquitous": False,
                        "value": "malicious",
                    }
                ],
            },
        ],
        "api_status_code": 200,
    }

    for entry in rsp.json["api_response"]:
        for annotation in entry["annotations"]:
            del annotation["timestamp"]

    assert rsp.status_code == 200
    assert rsp.json == expected


def test_detailed_hash_lookup(test_client, al_client, server):
    """Validate respone for a hash that exists."""
    data = al_client.responses["result"]
    digest = data["items"][0]["items"][0]["id"].split(".", 1)[0]

    # sha256 can use the result index
    rsp = test_client.get(f"/lookup/sha256/{dquote(digest)}/")
    expected = {
        "api_error_message": "",
        "api_response": [
            {
                "classification": "TLP:CLEAR",
                "count": 1,
                "annotations": [
                    {
                        "analytic": "Assemblyline - Services",
                        "quantity": 1,
                        "confidence": 1.0,
                        "summary": "1 Assemblyline service(s) flagged this file as malicious: ConfigExtractor",
                        "timestamp": ANY,
                        "type": "opinion",
                        "ubiquitous": False,
                        "value": "malicious",
                        "link": f"{server.AL_URL_BASE}/file/detail/{digest}",
                    }
                ],
            },
            {
                "classification": "TLP:CLEAR",
                "link": f"{server.AL_URL_BASE}/manage/safelist/{digest}",
                "count": 1,
                "annotations": [
                    {
                        "analytic": "Assemblyline - Safelist",
                        "confidence": 1.0,
                        "link": "https://assemblyline-ui/manage/safelist/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                        "quantity": 1,
                        "summary": "Assemblyline's safelist flagged this SHA256 as benign in 1 "
                        "source(s): urlhaus (external)",
                        "timestamp": ANY,
                        "type": "opinion",
                        "ubiquitous": False,
                        "value": "benign",
                    }
                ],
            },
            {
                "classification": "TLP:CLEAR",
                "link": f"{server.AL_URL_BASE}/manage/badlist/{digest}",
                "count": 1,
                "annotations": [
                    {
                        "analytic": "Assemblyline - Badlist",
                        "confidence": 1.0,
                        "link": "https://assemblyline-ui/manage/badlist/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                        "quantity": 1,
                        "summary": "Assemblyline's badlist flagged this SHA256 as malicious in 1 "
                        "source(s): urlhaus (external)",
                        "timestamp": ANY,
                        "type": "opinion",
                        "ubiquitous": False,
                        "value": "malicious",
                    }
                ],
            },
        ],
        "api_status_code": 200,
    }

    for entry in rsp.json["api_response"]:
        for annotation in entry["annotations"]:
            del annotation["timestamp"]

    assert rsp.status_code == 200, rsp.json["api_error_message"]
    assert rsp.json == expected


def test_submit_to_al(test_client, al_client, server):
    """Test the submit a URL to AL action."""
    rsp = test_client.post(
        "/actions/submit_url/",
        json={"selector": {"type": "url", "value": "https://google.ca"}, "internet_connected": True},
    )

    expected = {
        "api_error_message": "",
        "api_response": {
            "format": "markdown",
            "link": "https://assemblyline-ui/submission/detail/some-sid",
            "outcome": "success",
            "output": "Submitted to Assemblyline, submission ID: some-sid, internet " "connected: True",
            "summary": "Submitted to Assemblyline",
        },
        "api_status_code": 200,
    }

    assert rsp.status_code == 200, rsp.json["api_error_message"]
    assert rsp.json == expected
