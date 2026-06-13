import pytest

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
                "id": "305",
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


# Enrich
def test_enrich_returns_summary(enrich_result):
    assert enrich_result.annotations[0].summary == (
        "Threat Intel Team reported Payload delivery: Stop Ransomware: Medusa Ransomware"
    )


def test_enrich_count(enrich_result):
    assert enrich_result.count == 1


def test_enrich_classification(enrich_result):
    assert enrich_result.classification == "TLP:GREEN"


def test_enrich_value(enrich_result):
    assert enrich_result.annotations[0].value == "C2 beacon observed during Cobalt Strike campaign"


def test_enrich_confidence_sighting(enrich_result):
    assert enrich_result.annotations[0].confidence == 1.0


def test_enrich_confidence_no_sighting(app_module, base_params):
    app_module.lookup_type = lambda *a, **kw: [{**MISP_RESPONSE["Attribute"][0], "Sighting": []}]
    result = app_module.enrich(TEST_TYPE, TEST_IP, base_params)[0]
    assert result.annotations[0].confidence == 0.5


def test_enrich_freetext_comment_ignored(app_module, base_params):
    app_module.lookup_type = lambda *a, **kw: [
        {**MISP_RESPONSE["Attribute"][0], "comment": "Imported via the Freetext Import Tool"}
    ]
    result = app_module.enrich(TEST_TYPE, TEST_IP, base_params)[0]
    assert result.annotations[0].value != "Imported via the Freetext Import Tool"


# Helpers
@pytest.mark.parametrize(
    ("tag_name", "exp_ns", "exp_pred", "exp_val"),
    [
        ("tlp:red", "tlp", "red", ""),
        ("type:OSINT", "type", "OSINT", ""),
        ('misp-galaxy:mitre-attack="Exfiltration C2', "misp-galaxy", "mitre-attack", "Exfiltration C2"),
    ],
)
def test__parse_misp_tag(tag_name, exp_ns, exp_pred, exp_val):
    import app

    ns, pred, val = app._parse_misp_tag(tag_name)
    assert ns == exp_ns
    assert pred == exp_pred
    assert val == exp_val


def test__process_tags():
    import app

    original = app.ALLOW_TAGS
    app.ALLOW_TAGS = {"misp-galaxy:threat-actor"}
    sample_tags = [
        {"name": "type:OSINT"},
        {"name": "tlp:red"},
        {"name": 'osint:lifetime="perpetual"'},
        {"name": 'misp-galaxy:threat-actor="APT 29"'},
    ]

    tags, labels = app._process_tags(sample_tags)
    assert tags == {"threat-actor:APT 29"}
    assert labels == {"APT 29", "OSINT"}

    app.ALLOW_TAGS = original


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
