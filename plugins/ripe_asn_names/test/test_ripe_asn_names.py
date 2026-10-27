import pytest
from clue.common.exceptions import InvalidDataException
from clue.plugin.utils import Params
from ripe_asn_names import app


def make_params(raw: bool = True, annotate: bool = True, limit: int = 10) -> Params:
    return Params(raw=raw, deadline=9999999999, max_timeout=10, annotate=annotate, limit=limit, use_cache=False)


@pytest.fixture(autouse=True)
def asn_records(monkeypatch):
    records = {
        15169: app.AsnRecord("GOOGLE - Google LLC", "US"),
        64496: app.AsnRecord("EXAMPLE - Example, Incorporated", "CA"),
        64497: app.AsnRecord("EXAMPLE - No country", None),
    }
    monkeypatch.setattr(app, "ASN_RECORDS", records)
    return records


def test_parse_asn_data_extracts_country_and_preserves_commas():
    records = app.parse_asn_data(
        [
            "15169 GOOGLE - Google LLC, US\n",
            "64496 EXAMPLE - Example, Incorporated, CA\n",
            "malformed\n",
        ]
    )

    assert records[15169] == app.AsnRecord("GOOGLE - Google LLC", "US")
    assert records[64496] == app.AsnRecord("EXAMPLE - Example, Incorporated", "CA")
    assert len(records) == 2


def test_parse_asn_data_ignores_blank_comment_and_malformed_lines(caplog):
    records = app.parse_asn_data(["\n", "  # Comment\n", "invalid Example, CA\n", "64496\n"])

    assert records == {}
    assert "Ignoring malformed ASN record on line 3" in caplog.text
    assert "Ignoring malformed ASN record on line 4" in caplog.text


@pytest.mark.parametrize("description", ["EXAMPLE", "EXAMPLE, Incorporated", "EXAMPLE, usa", "EXAMPLE, us"])
def test_parse_asn_data_preserves_descriptions_without_country_code(description):
    assert app.parse_asn_data([f"64496 {description}"]) == {64496: app.AsnRecord(description, None)}


def test_load_asn_data_reads_utf8_dataset(tmp_path):
    path = tmp_path / "asn.txt"
    path.write_text("64496 EXAMPLE - Société, CA\n", encoding="utf-8")

    assert app.load_asn_data(path) == {64496: app.AsnRecord("EXAMPLE - Société", "CA")}


def test_load_asn_data_returns_empty_lookup_for_missing_file(tmp_path, caplog):
    path = tmp_path / "missing.txt"

    assert app.load_asn_data(path) == {}
    assert f"Unable to load RIPE ASN data from {path}" in caplog.text


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("15169", 15169),
        (" as15169 ", 15169),
        ("As0015169", 15169),
        ("0", 0),
        ("AS4294967295", 4294967295),
        ("", None),
        ("AS", None),
        ("AS-not-a-number", None),
        ("AS²", None),
        ("AS 15169", None),
        ("-1", None),
        ("+15169", None),
        ("15169.0", None),
        ("1.10", None),
        ("4294967296", None),
    ],
)
def test_normalize_asn_accepts_common_formats_and_rejects_invalid_values(value, expected):
    assert app.normalize_asn(value) == expected


@pytest.mark.parametrize("value", ["15169", "AS15169", " as15169 "])
def test_enrich_returns_name_country_and_raw_data(value):
    result = app.enrich("asn", value, make_params(), None)

    assert result.classification == app.CLASSIFICATION
    assert result.count == 1
    assert result.raw_data == {
        "asn": 15169,
        "name": "GOOGLE - Google LLC",
        "country_code": "US",
        "source": "RIPE NCC ASN Names",
    }
    assert len(result.annotations) == 1
    annotation = result.annotations[0]
    assert annotation.value == "GOOGLE - Google LLC"
    assert annotation.analytic == "RIPE ASN Names"
    assert annotation.type == "context"
    assert annotation.confidence == 1.0
    assert "AS15169" in annotation.summary
    assert "(US)" in annotation.summary


@pytest.mark.parametrize(("raw", "annotate"), [(False, True), (True, False), (False, False), (True, True)])
def test_enrich_respects_output_flags(raw, annotate):
    result = app.enrich("asn", "AS15169", make_params(raw=raw, annotate=annotate), None)

    assert result.count == 1
    assert (result.raw_data is not None) is raw
    assert bool(result.annotations) is annotate


def test_enrich_respects_zero_annotation_limit():
    result = app.enrich("asn", "AS64496", make_params(limit=0), None)

    assert result.count == 1
    assert result.raw_data["asn"] == 64496
    assert result.annotations == []


def test_enrich_without_country_code():
    result = app.enrich("asn", "AS64497", make_params(), None)

    assert result.count == 1
    assert result.raw_data["country_code"] is None
    assert result.annotations[0].summary == (
        "AS64497 is registered as EXAMPLE - No country in the RIPE ASN names dataset."
    )


@pytest.mark.parametrize("value", ["AS64498", "AS-not-a-number", "AS²", "4294967296"])
def test_enrich_returns_empty_entry_for_unknown_or_invalid_asn(value):
    result = app.enrich("asn", value, make_params(), None)

    assert result.classification == app.CLASSIFICATION
    assert result.count == 0
    assert result.annotations == []
    assert result.raw_data is None


def test_enrich_returns_empty_entry_for_missing_dataset(monkeypatch):
    monkeypatch.setattr(app, "ASN_RECORDS", {})

    result = app.enrich("asn", "AS15169", make_params(), None)

    assert result.count == 0
    assert result.annotations == []


def test_enrich_rejects_unsupported_type():
    with pytest.raises(InvalidDataException, match="Type name `domain` is invalid"):
        app.enrich("domain", "15169", make_params(), None)


def test_plugin_advertises_asn_type():
    response = app.plugin.app.test_client().get("/types/")

    assert response.status_code == 200
    assert response.json["api_error_message"] == ""
    assert response.json["api_response"] == {"asn": app.CLASSIFICATION}
    assert app.plugin.cache is None


def test_lookup_serializes_enrichment():
    response = app.plugin.app.test_client().get("/lookup/asn/AS64496/?include_raw=true")

    assert response.status_code == 200
    assert response.json["api_error_message"] == ""
    result = response.json["api_response"][0]
    assert result["count"] == 1
    assert result["classification"] == app.CLASSIFICATION
    assert result["raw_data"]["asn"] == 64496
    assert result["annotations"][0]["value"] == "EXAMPLE - Example, Incorporated"


@pytest.mark.parametrize("query", ["no_annotation=true", "limit=0"])
def test_lookup_respects_annotation_controls(query):
    response = app.plugin.app.test_client().get(f"/lookup/asn/AS64496/?{query}")

    assert response.status_code == 200
    result = response.json["api_response"][0]
    assert result["count"] == 1
    assert result["annotations"] == []
    assert "raw_data" not in result


def test_lookup_rejects_unsupported_type():
    response = app.plugin.app.test_client().get("/lookup/domain/15169/")

    assert response.status_code == 422
    assert "Invalid type name" in response.json["api_error_message"]


def test_bulk_lookup_returns_matches_and_empty_entries():
    response = app.plugin.app.test_client().post(
        "/lookup/?include_raw=true",
        json=[
            {"type": "asn", "value": "AS64496"},
            {"type": "asn", "value": "AS64498"},
        ],
    )

    assert response.status_code == 200
    assert response.json["api_error_message"] == ""
    entries = response.json["api_response"]["asn"]
    assert entries["AS64496"]["items"][0]["count"] == 1
    assert entries["AS64496"]["items"][0]["raw_data"]["asn"] == 64496
    assert entries["AS64498"]["items"][0]["count"] == 0
