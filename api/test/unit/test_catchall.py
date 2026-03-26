from datetime import datetime, timezone
from unittest.mock import patch

from clue.models.network import parse_datetime


class TestParseDatetime:
    def test_returns_none_for_none(self):
        assert parse_datetime(None) is None

    def test_passthrough_datetime_object(self):
        dt = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert parse_datetime(dt) is dt

    def test_parses_iso_string(self):
        result = parse_datetime("2024-01-01T01:01:01")
        assert result == datetime(2024, 1, 1, 1, 1, 1)

    def test_parses_iso_string_with_utc_offset(self):
        result = parse_datetime("2024-01-01T01:01:01+00:00")
        assert result == datetime(2024, 1, 1, 1, 1, 1, tzinfo=timezone.utc)

    def test_parses_z_suffix_as_utc(self):
        result = parse_datetime("2024-01-01T01:01:01Z")
        assert result == datetime(2024, 1, 1, 1, 1, 1, tzinfo=timezone.utc)

    def test_returns_none_for_invalid_string(self):
        with patch("clue.models.network.logger.exception"):
            assert parse_datetime("not-a-date") is None

    def test_returns_none_for_empty_string(self):
        with patch("clue.models.network.logger.exception"):
            assert parse_datetime("") is None
