from datetime import datetime, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from clue.models.sync import ChangeRow, SelectorDocument


def _doc(**overrides) -> dict:
    defaults = {
        "id": "abc123",
        "updated_at": 1234567890,
        "_deleted": False,
        "type": "ip",
        "value": "127.0.0.1",
        "source": "example",
    }
    defaults.update(overrides)
    return defaults


def test_change_row_valid_minimal():
    row = TypeAdapter(list[ChangeRow]).validate_python([{"newDocumentState": _doc()}], strict=True, by_alias=True)[0]
    assert isinstance(row.new_document_state, SelectorDocument)
    assert row.assumed_master_state is None


def test_change_row_with_assumed_master_state():
    rows = TypeAdapter(list[ChangeRow]).validate_python(
        [{"newDocumentState": _doc(), "assumedMasterState": _doc()}], strict=True, by_alias=True
    )
    assert rows[0].assumed_master_state is not None


def test_change_row_accepts_iso_string_expiry_in_strict_mode():
    """Regression test: RxDB clients send expiry as an ISO datetime string, which must
    still validate under strict=True (see the Timestamp alias on QueryEntry.expiry)."""
    rows = TypeAdapter(list[ChangeRow]).validate_python(
        [{"newDocumentState": _doc(expiry="2026-07-30T17:54:09.902000")}], strict=True, by_alias=True
    )
    assert rows[0].new_document_state.expiry == datetime(2026, 7, 30, 17, 54, 9, 902000)


def test_change_row_accepts_z_suffix_expiry_in_strict_mode():
    rows = TypeAdapter(list[ChangeRow]).validate_python(
        [{"newDocumentState": _doc(expiry="2026-07-30T17:54:09.902000Z")}], strict=True, by_alias=True
    )
    assert rows[0].new_document_state.expiry == datetime(2026, 7, 30, 17, 54, 9, 902000, tzinfo=timezone.utc)


def test_change_row_accepts_datetime_object_expiry_in_strict_mode():
    expiry = datetime(2026, 7, 30, tzinfo=timezone.utc)
    rows = TypeAdapter(list[ChangeRow]).validate_python(
        [{"newDocumentState": _doc(expiry=expiry)}], strict=True, by_alias=True
    )
    assert rows[0].new_document_state.expiry == expiry


def test_change_row_accepts_null_expiry():
    rows = TypeAdapter(list[ChangeRow]).validate_python(
        [{"newDocumentState": _doc(expiry=None)}], strict=True, by_alias=True
    )
    assert rows[0].new_document_state.expiry is None


def test_change_row_rejects_missing_required_field():
    doc = _doc()
    del doc["type"]
    with pytest.raises(ValidationError):
        TypeAdapter(list[ChangeRow]).validate_python([{"newDocumentState": doc}], strict=True, by_alias=True)


def test_change_row_rejects_unparseable_expiry():
    """parse_datetime swallows unparseable strings into None, which then fails the
    inner `datetime` schema of the `Timestamp | None` union, surfacing as a ValidationError."""
    with pytest.raises(ValidationError):
        TypeAdapter(list[ChangeRow]).validate_python(
            [{"newDocumentState": _doc(expiry="not-a-date")}], strict=True, by_alias=True
        )
