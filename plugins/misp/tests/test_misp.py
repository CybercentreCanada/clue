from datetime import datetime, timezone

import pytest
from clue.common.exceptions import UnprocessableException
from clue.models.selector import Selector
from clue.plugin.utils import Params

TEST_PATH = "/attributes/restSearch"

TEST_IP = "198.51.100.42"
TEST_TYPE = "ipv4"

MISP_RESPONSE = {
    "Attribute": [
        {
            "id": "82741",
            "event_id": "305",
            "category": "Payload delivery",
            "type": "ip-src",
            "comment": "C2 beacon observed during Cobalt Strike campaign",
            "value": "198.51.100.42",
            "timestamp": "1576589519",
            "threat_level_id": "1",
            "Sighting": [
                {
                    "date_sighting": "1781380901",
                    "type": "0",
                },
                {
                    "date_sighting": "1781380907",
                    "type": "0",
                },
            ],
            "Event": {
                "info": "Stop Ransomware: Medusa Ransomware",
                "date": "2026-06-01",
                "threat_level_id": "1",
                "Org": {"name": "Acme SOC"},
                "Orgc": {"name": "Threat Intel Team"},
            },
            "Tag": [
                {"name": "kill-chain:Command and Control"},
                {"name": 'adversary:infrastructure-type="C2"'},
                {"name": "tlp:green"},
            ],
        }
    ]
}


@pytest.fixture()
def app():
    import app

    return app


@pytest.fixture()
def enrichments():
    import enrichments

    return enrichments


@pytest.fixture()
def mock_lookup(app, monkeypatch):
    """Patch lookup_attributes to return a sample attribute, merged with optional overrides"""

    def _mock(overrides=None):
        def _patched(*args, **kwargs):
            return [{**MISP_RESPONSE["Attribute"][0], **(overrides or {})}]

        monkeypatch.setattr(app, "lookup_attributes", _patched)
        return app

    return _mock


@pytest.fixture()
def base_params():
    return Params(
        deadline=0,
        max_timeout=1,
        annotate=True,
        raw=False,
        limit=10,
        use_cache=False,
    )


@pytest.fixture()
def enrich_result(mock_lookup, base_params):
    return mock_lookup().enrich(TEST_TYPE, TEST_IP, base_params)[0]


def test_enrich(enrich_result):
    assert enrich_result.count == 1
    assert enrich_result.classification == "TLP:GREEN"

    annotation = enrich_result.annotations[0]
    assert annotation.summary == "Threat Intel Team reported Payload delivery: Stop Ransomware: Medusa Ransomware"
    assert annotation.value == "C2 beacon observed during Cobalt Strike campaign"
    assert annotation.confidence == 0.9
    assert annotation.quantity == 2
    assert annotation.severity == 0.75


def test_enrich_no_annotate(mock_lookup, base_params):
    base_params.annotate = False
    result = mock_lookup().enrich(TEST_TYPE, TEST_IP, base_params)
    assert len(result) == 1
    assert result[0].annotations == []


def test_enrich_missing_timestamp(mock_lookup, base_params):
    app = mock_lookup({"last_seen": None, "timestamp": None})
    with pytest.raises(UnprocessableException):
        app.enrich(TEST_TYPE, TEST_IP, base_params)


def test_enrich_raw_data(mock_lookup, base_params):
    base_params.raw = True
    result = mock_lookup().enrich(TEST_TYPE, TEST_IP, base_params)[0]
    assert result.raw_data is not None


def test_enrich_freetext_comment_ignored(mock_lookup, base_params):
    app = mock_lookup({"comment": "Imported via the Freetext Import Tool"})
    result = app.enrich(TEST_TYPE, TEST_IP, base_params)[0]
    assert result.annotations[0].value != "Imported via the Freetext Import Tool"


def test_enrich_confidence_no_sighting(mock_lookup, base_params):
    app = mock_lookup({"Sighting": []})
    result = app.enrich(TEST_TYPE, TEST_IP, base_params)[0]
    assert result.annotations[0].confidence == 0.5


def test_enrich_severity_none(mock_lookup, base_params):
    app = mock_lookup({"Event": {"threat_level_id": "0"}})
    result = app.enrich(TEST_TYPE, TEST_IP, base_params)[0]
    assert result.annotations[0].severity is None


def test_enrich_timestamp_no_sightings(mock_lookup, base_params):
    app = mock_lookup({"last_seen": None, "timestamp": "1576589519"})
    result = app.enrich(TEST_TYPE, TEST_IP, base_params)[0]
    assert result.annotations[0].timestamp == datetime.fromtimestamp(1576589519, tz=timezone.utc)


def test_enrich_active_range_in_details(mock_lookup, base_params):
    app = mock_lookup({"first_seen": "2026-01-01T00:00:00Z", "last_seen": "2026-06-01T00:00:00Z"})
    result = app.enrich(TEST_TYPE, TEST_IP, base_params)[0]
    assert "Active: 2026-01-01 - 2026-06-01" in result.annotations[0].details


# Helpers
@pytest.mark.parametrize(
    ("tag_name", "exp_ns", "exp_pred", "exp_val"),
    [
        ("tlp:red", "tlp", "red", ""),
        ("type:OSINT", "type", "OSINT", ""),
        ('misp-galaxy:mitre-attack="Exfiltration C2"', "misp-galaxy", "mitre-attack", "Exfiltration C2"),
        ('misp-galaxy:mitre-attack="Exfiltration C2', "misp-galaxy", "mitre-attack", "Exfiltration C2"),
        ("adversary:infrastructure-type='C2'", "adversary", "infrastructure-type", "C2"),
    ],
)
def test__parse_misp_tag(enrichments, tag_name, exp_ns, exp_pred, exp_val):
    ns, pred, val = enrichments._parse_misp_tag(tag_name)
    assert ns == exp_ns
    assert pred == exp_pred
    assert val == exp_val


@pytest.mark.parametrize(
    ("sample_tags", "exp_tags", "exp_labels"),
    [
        (
            [
                {"name": "type:OSINT"},
                {"name": "tlp:red"},
                {"name": 'osint:lifetime="perpetual"'},
                {"name": 'misp-galaxy:threat-actor="APT 29"'},
            ],
            {"threat-actor:APT 29"},
            {"APT 29", "OSINT"},
        ),
        ([{"name": 'ecsirt="malware"'}], {"ecsirt:malware"}, set()),
        ([{"name": "tlp:red"}, {"name": 'osint:lifetime="perpetual"'}], set(), set()),
        ([], set(), set()),
    ],
    ids=["allowlisted", "namespace_only", "no_match", "empty"],
)
def test__process_tags(enrichments, monkeypatch, sample_tags, exp_tags, exp_labels):
    monkeypatch.setattr(enrichments, "ALLOW_TAGS", {"misp-galaxy:threat-actor", "ecsirt"})
    tags, labels = enrichments._process_tags(sample_tags)
    assert tags == exp_tags
    assert labels == exp_labels


def test__highest_tlp(enrichments):
    assert enrichments._highest_tlp(["TLP:GREEN", "TLP:RED", "TLP:WHITE", "TLP:AMBER"]) == "TLP:RED"
    assert enrichments._highest_tlp(["TLP:AMBER+STRICT", "TLP:AMBER"]) == "TLP:AMBER+STRICT"
    assert enrichments._highest_tlp(["TLP:GREEN"]) == "TLP:GREEN"
    assert enrichments._highest_tlp(["tlp:green"]) == "TLP:GREEN"
    assert enrichments._highest_tlp([]) is None


# Client
@pytest.fixture()
def client(monkeypatch):
    import client

    monkeypatch.setattr(client, "MISP_API_KEY", "test-key")
    return client


def test_misp_request_no_api_key(client, monkeypatch):
    monkeypatch.setattr(client, "MISP_API_KEY", "")

    with pytest.raises(UnprocessableException):
        client.misp_request("post", TEST_PATH, 3)


# Actions
@pytest.fixture()
def sighting_action(app):
    from actions import ReportSighting
    from clue.models.actions import Action
    from consts import CLASSIFICATION, TYPE_MAPPING

    return Action[ReportSighting](
        id="report_sighting",
        name="Report a sighting",
        classification=CLASSIFICATION,
        supported_types=set(TYPE_MAPPING.keys()),
    )


@pytest.fixture()
def sighting_requests(monkeypatch):
    import actions

    calls = []

    def fake_misp_request(method, path, timeout, **kwargs):
        calls.append({"method": method, "path": path, "timeout": timeout, **kwargs})
        return {"Sighting": {"id": "77"}}

    monkeypatch.setattr(actions, "misp_request", fake_misp_request)
    return calls


@pytest.mark.parametrize(
    ("sighting_type", "type_id"),
    [
        ("true positive", "0"),
        ("false positive", "1"),
    ],
)
def test_run_action(app, sighting_action, sighting_requests, sighting_type, type_id):
    from actions import ReportSighting
    from consts import MAX_TIMEOUT, SIGHTING_SOURCE

    request = ReportSighting(selectors=[Selector(type=TEST_TYPE, value=TEST_IP)], sighting_type=sighting_type)

    result = app.run_action(sighting_action, request, None)

    assert sighting_requests == [
        {
            "method": "post",
            "path": "/sightings/add",
            "timeout": MAX_TIMEOUT,
            "json": {"values": [TEST_IP], "type": type_id, "source": SIGHTING_SOURCE},
        },
    ]

    assert result.outcome == "success"
    assert result.format == "markdown"
    assert result.summary == "Reported sighting to MISP"
    assert result.output == f"Reported sighting for `{TEST_IP}` as **{sighting_type}**."


def test_run_action_invalid_id(app, sighting_action, sighting_requests):
    from actions import ReportSighting

    sighting_action.id = "unsupported_action"
    request = ReportSighting(selectors=[Selector(type=TEST_TYPE, value=TEST_IP)])

    result = app.run_action(sighting_action, request, None)

    assert result.outcome == "failure"
    assert result.summary == "invalid action ID: unsupported_action"
    assert sighting_requests == []


def test_run_action_no_match(app, sighting_action, monkeypatch):
    import actions
    from actions import ReportSighting

    monkeypatch.setattr(
        actions,
        "misp_request",
        lambda *a, **kw: {"message": "Could not add the Sighting. Reason: No valid attributes found."},
    )
    request = ReportSighting(selectors=[Selector(type=TEST_TYPE, value=TEST_IP)])

    result = app.run_action(sighting_action, request, None)

    assert result.outcome == "failure"
    assert result.summary == "MISP recorded no sightings, no attribute matched."
