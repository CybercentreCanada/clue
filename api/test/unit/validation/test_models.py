from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from clue.models.network import Annotation, QueryEntry, QueryResult


def test_query_result():
    QueryResult.model_validate(
        {"type": "ip", "value": "127.0.0.1", "source": "example", "items": [], "error": "It's broken"}
    )
    with pytest.raises(ValidationError):
        QueryResult.model_validate({"type": "ip", "value": "127.0.0.1", "source": "example", "items": [], "error": 1})

    QueryResult.model_validate(
        {
            "type": "ip",
            "value": "127.0.0.1",
            "source": "example",
            "items": [{"count": 1, "link": "http://example.com", "annotations": [], "raw_data": []}],
        }
    )

    with pytest.raises(ValidationError):
        QueryResult.model_validate(
            {
                "type": "ip",
                "value": "127.0.0.1",
                "source": "example",
                "items": [{"count": 1, "link": "Not a url", "annotations": []}],
            }
        )

    with pytest.raises(ValidationError):
        QueryResult.model_validate(
            {
                "type": "ip",
                "value": "127.0.0.1",
                "source": "example",
                "items": [{"count": "one", "link": "Not a url", "annotations": []}],
            }
        )

    QueryResult.model_validate(
        {
            "type": "ip",
            "value": "127.0.0.1",
            "source": "example",
            "items": [
                {
                    "count": 1,
                    "link": "http://example.com",
                    "annotations": [
                        {
                            "analytic": "test",
                            "type": "opinion",
                            "value": "malicious",
                            "confidence": 0.5,
                            "severity": 1.0,
                            "summary": "test",
                            "details": "test",
                            "classification": "TLP:WHITE",
                            "version": "0.0.1",
                        }
                    ],
                    "raw_data": [{"classification": "TLP:CLEAR", "data": '{"test": "data"}'}],
                }
            ],
        }
    )

    with pytest.raises(ValidationError):
        QueryResult.model_validate(
            {
                "type": "ip",
                "value": "127.0.0.1",
                "source": "example",
                "items": [
                    {
                        "count": 1,
                        "link": "http://example.com",
                        "annotations": [
                            {
                                "analytic": "test",
                                "type": "not a valid type",
                                "value": "test",
                                "confidence": 0.5,
                                "severity": 1.0,
                                "summary": "test",
                                "details": "test",
                                "classification": "TLP:WHITE",
                                "version": "0.0.1",
                            }
                        ],
                        "raw_data": [{"classification": "TLP:CLEAR", "data": '{"test": "data"}'}],
                    }
                ],
            }
        )


def test_query_entry():
    QueryEntry.model_validate({"count": 1, "link": "https://example.com", "annotations": [], "raw_data": []})

    with pytest.raises(ValidationError):
        QueryEntry.model_validate(
            {
                "count": 1,
                "link": "https://example.com",
                "annotations": [{"aaaa": "bbbb"}],
                "raw_data": [{"classification": "TLP:CLEAR", "data": '{"test": "data"}'}],
            }
        )


def test_annotation_validation():
    QueryEntry.model_validate(
        {
            "classification": "TLP:WHITE",
            "count": 1,
            "link": "https://example.com",
            "annotations": [
                {
                    "analytic": "test",
                    "type": "opinion",
                    "value": "malicious",
                    "confidence": 0.5,
                    "severity": 1.0,
                    "summary": "test",
                    "version": "0.0.1",
                },
                {
                    "analytic": "test",
                    "type": "frequency",
                    "value": "100",
                    "confidence": 0.5,
                    "severity": 1.0,
                    "summary": "test",
                    "version": "0.0.1",
                },
                {
                    "analytic": "test",
                    "type": "frequency",
                    "value": 1.1,
                    "confidence": 0.5,
                    "severity": 1.0,
                    "summary": "test",
                    "version": "0.0.1",
                },
            ],
            "raw_data": [{"classification": "TLP:CLEAR", "data": '{"test": "data"}'}],
        }
    )

    # Test invalid frequency
    with pytest.raises(ValidationError) as err:
        QueryEntry.model_validate(
            {
                "classification": "TLP:WHITE",
                "count": 1,
                "link": "https://example.com",
                "annotations": [
                    {
                        "analytic": "test",
                        "type": "frequency",
                        "value": "test",
                        "confidence": 0.5,
                        "severity": 1.0,
                        "summary": "test",
                        "version": "0.0.1",
                    }
                ],
                "raw_data": [{"classification": "TLP:CLEAR", "data": '{"test": "data"}'}],
            }
        )

    assert "Value must be an int if type is frequency" in err.value.errors()[0]["msg"]

    with pytest.raises(ValidationError) as err:
        QueryEntry.model_validate(
            {
                "classification": "TLP:WHITE",
                "count": 1,
                "link": "https://example.com",
                "annotations": [
                    {
                        "analytic": "test",
                        "type": "opinion",
                        "value": 1234,
                        "confidence": 0.5,
                        "severity": 1.0,
                        "summary": "test",
                        "version": "0.0.1",
                    }
                ],
                "raw_data": [{"classification": "TLP:CLEAR", "data": '{"test": "data"}'}],
            }
        )

    assert "Value must be a string if type is not frequency" in err.value.errors()[0]["msg"]

    with pytest.raises(ValidationError) as err:
        QueryEntry.model_validate(
            {
                "classification": "TLP:WHITE",
                "count": 1,
                "link": "https://example.com",
                "annotations": [
                    {
                        "analytic": "test",
                        "type": "opinion",
                        "value": "potato",
                        "confidence": 0.5,
                        "severity": 1.0,
                        "summary": "test",
                        "version": "0.0.1",
                    }
                ],
                "raw_data": [{"classification": "TLP:CLEAR", "data": '{"test": "data"}'}],
            }
        )

    assert "If type is opinion, value must be one of (" in err.value.errors()[0]["msg"]


def test_annotation_timestamp_defaults_to_datetime():
    annotation = Annotation.model_validate(
        {
            "analytic": "test",
            "type": "opinion",
            "value": "malicious",
            "confidence": 0.5,
            "summary": "test",
        }
    )

    assert isinstance(annotation.timestamp, datetime)


def test_annotation_timestamp_parses_iso_string():
    annotation = Annotation.model_validate(
        {
            "analytic": "test",
            "type": "opinion",
            "value": "malicious",
            "confidence": 0.5,
            "summary": "test",
            "timestamp": "2024-01-01T01:01:01Z",
        }
    )

    assert annotation.timestamp == datetime(2024, 1, 1, 1, 1, 1, tzinfo=timezone.utc)


def test_annotation_timestamp_rejects_invalid_string():
    with pytest.raises(ValidationError):
        Annotation.model_validate(
            {
                "analytic": "test",
                "type": "opinion",
                "value": "malicious",
                "confidence": 0.5,
                "summary": "test",
                "timestamp": "not-a-date",
            }
        )
