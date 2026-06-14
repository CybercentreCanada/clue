import pytest
from datetime import datetime, timezone

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
def app_module():
    import app

    app.lookup_type = lambda *a, **kw: MISP_RESPONSE["Attribute"]
    return app


def override_attr(app_module, overrides):
    """Mock lookup_type with attribute field overrides"""
    app_module.lookup_type = lambda *a, **kw: [{**MISP_RESPONSE["Attribute"][0], **overrides}]


@pytest.fixture()
def base_params(app_module):
    return app_module.Params(
        deadline=0,
        max_timeout=1,
        annotate=True,
        raw=False,
        limit=10,
        use_cache=False,
    )


@pytest.fixture()
def enrich_result(app_module, base_params):
    return app_module.enrich(TEST_TYPE, TEST_IP, base_params)[0]


def test_enrich_count(enrich_result):
    assert enrich_result.count == 1


def test_enrich_classification(enrich_result):
    assert enrich_result.classification == "TLP:GREEN"


def test_enrich_raw_data(app_module, base_params):
    base_params.raw = True
    result = app_module.enrich(TEST_TYPE, TEST_IP, base_params)[0]
    assert result.raw_data is not None


def test_enrich_returns_summary(enrich_result):
    assert enrich_result.annotations[0].summary == (
        "Threat Intel Team reported Payload delivery: Stop Ransomware: Medusa Ransomware"
    )


def test_enrich_value(enrich_result):
    assert enrich_result.annotations[0].value == "C2 beacon observed during Cobalt Strike campaign"


def test_enrich_freetext_comment_ignored(app_module, base_params):
    override_attr(app_module, {"comment": "Imported via the Freetext Import Tool"})
    result = app_module.enrich(TEST_TYPE, TEST_IP, base_params)[0]
    assert result.annotations[0].value != "Imported via the Freetext Import Tool"


def test_enrich_confidence_sighting(enrich_result):
    assert enrich_result.annotations[0].confidence == 0.9


def test_enrich_confidence_no_sighting(app_module, base_params):
    override_attr(app_module, {"Sighting": []})
    result = app_module.enrich(TEST_TYPE, TEST_IP, base_params)[0]
    assert result.annotations[0].confidence == 0.5


def test_enrich_sighting_quantity(enrich_result):
    assert enrich_result.annotations[0].quantity == 2


def test_enrich_severity(enrich_result):
    assert enrich_result.annotations[0].severity == 0.75


def test_enrich_severity_none(app_module, base_params):
    override_attr(
        app_module,
        {
            "Event": {
                "date": "2026-06-01",
                "threat_level_id": "0",
            }
        },
    )
    result = app_module.enrich(TEST_TYPE, TEST_IP, base_params)[0]
    assert result.annotations[0].severity is None


def test_enrich_timestamp_no_sightings(app_module, base_params):
    override_attr(app_module, {"last_seen": None, "timestamp": "1576589519"})
    result = app_module.enrich(TEST_TYPE, TEST_IP, base_params)[0]
    assert result.annotations[0].timestamp == datetime.fromtimestamp(1576589519, tz=timezone.utc)


def test_enrich_active_range_in_details(app_module, base_params):
    override_attr(app_module, {"first_seen": "2026-01-01T00:00:00Z", "last_seen": "2026-06-01T00:00:00Z"})
    result = app_module.enrich(TEST_TYPE, TEST_IP, base_params)[0]
    assert "Active: 2026-01-01 - 2026-06-01" in result.annotations[0].details


# Helpers
@pytest.mark.parametrize(
    ("tag_name", "exp_ns", "exp_pred", "exp_val"),
    [
        ("tlp:red", "tlp", "red", ""),
        ("type:OSINT", "type", "OSINT", ""),
        ('misp-galaxy:mitre-attack="Exfiltration C2"', "misp-galaxy", "mitre-attack", "Exfiltration C2"),
        ('misp-galaxy:mitre-attack="Exfiltration C2', "misp-galaxy", "mitre-attack", "Exfiltration C2"),
    ],
)
def test__parse_misp_tag(tag_name, exp_ns, exp_pred, exp_val):
    import app

    ns, pred, val = app._parse_misp_tag(tag_name)
    assert ns == exp_ns
    assert pred == exp_pred
    assert val == exp_val


def test__process_tags(monkeypatch):
    import app

    monkeypatch.setattr(app, "ALLOW_TAGS", {"misp-galaxy:threat-actor"})
    sample_tags = [
        {"name": "type:OSINT"},
        {"name": "tlp:red"},
        {"name": 'osint:lifetime="perpetual"'},
        {"name": 'misp-galaxy:threat-actor="APT 29"'},
    ]

    tags, labels = app._process_tags(sample_tags)
    assert tags == {"threat-actor:APT 29"}
    assert labels == {"APT 29", "OSINT"}


def test__process_tags_no_match():
    import app

    sample_tags = [
        {"name": "tlp:red"},
        {"name": 'osint:lifetime="perpetual"'},
    ]
    tags, labels = app._process_tags(sample_tags)
    assert tags == set()
    assert labels == set()


def test__process_tags_empty():
    import app

    tags, labels = app._process_tags([])
    assert tags == set()
    assert labels == set()


def test__highest_tlp():
    import app

    assert app._highest_tlp(["TLP:GREEN", "TLP:RED", "TLP:WHITE", "TLP:AMBER"]) == "TLP:RED"
    assert app._highest_tlp(["TLP:GREEN"]) == "TLP:GREEN"
    assert app._highest_tlp(["tlp:green"]) == "TLP:GREEN"
    assert app._highest_tlp([]) is None
