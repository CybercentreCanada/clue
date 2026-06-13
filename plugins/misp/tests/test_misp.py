import pytest

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
                {"id": "12", "type": "0", "date_sighting": "1749123600", "Organisation": {"name": "Acme SOC"}},
                {"id": "13", "type": "0", "date_sighting": "1749210000", "Organisation": {"name": "Acme SOC"}},
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
                {"name": "kill-chain:Command and Control", "colour": "#a80079"},
                {"name": 'adversary:infrastructure-type="C2"', "colour": "#ff6600"},
                {"name": "tlp:green", "colour": "#00cc00"},
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


# Enrich
def test_enrich_returns_summary(app_module, base_params):
    result = app_module.enrich("ipv4", "198.51.100.42", base_params)[0]
    assert result.annotations[0].summary == (
        "Threat Intel Team reported Payload delivery: Stop Ransomware: Medusa Ransomware"
    )


def test_enrich_count(app_module, base_params):
    result = app_module.enrich("ipv4", "198.51.100.42", base_params)[0]
    assert result.count == 1


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
    app.ALLOW_TAGS = {
        "misp-galaxy:threat-actor"
    }
    sample_tags = [
        {"name":"type:OSINT"},
        {"name":"tlp:red"},
        {"name":'osint:lifetime="perpetual"'},
        {"name":'misp-galaxy:threat-actor="APT 29"'},
    ]

    tags, labels = app._process_tags(sample_tags)
    assert tags == {'threat-actor:APT 29'}
    assert labels == {'APT 29', 'OSINT'}

    app.ALLOW_TAGS = original


def test__process_tags_no_match():
    import app
    sample_tags = [
        {"name": "tlp:red"},
        {"name": "osint:lifetime=\"perpetual\""},
    ]
    tags, labels = app._process_tags(sample_tags)
    assert tags == set()
    assert labels == set()


def test__process_tags_empty():
    import app
    tags, labels = app._process_tags([])
    assert len(tags) == 0
    assert len(labels) == 0
