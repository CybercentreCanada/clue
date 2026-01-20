"""Test suite for handling non-serializable data in plugin responses.

This module tests the scenario where a QueryEntry object contains non-serializable
data (e.g., a requests.Response object in raw_data), which would cause a serialization
error when attempting to convert the response to JSON.
"""

import logging
from unittest.mock import Mock

import pytest
from pydantic_core import Url

from clue.models.network import Annotation, QueryEntry
from clue.plugin import CluePlugin


class NonSerializableObject:
    """A custom class that cannot be JSON serialized."""

    def __init__(self, data: str):
        self.data = data
        self._internal_ref = self  # Circular reference to ensure non-serializability


@pytest.fixture
def mock_requests_response():
    """Create a mock requests.Response object (non-serializable)."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = '{"key": "value"}'
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = {"key": "value"}
    # Make it explicitly non-serializable
    mock_response.__class__ = type("Response", (), {})
    return mock_response


@pytest.fixture
def plugin_with_non_serializable_response(mock_requests_response):
    """Create a CluePlugin that returns QueryEntry with non-serializable raw_data."""

    def enrich_with_bad_data(type_name: str, value: str, params, token):
        """Enrich function that returns non-serializable data in raw_data field."""
        return QueryEntry(
            count=1,
            classification="TLP:CLEAR",
            link=Url("https://example.com/data"),
            annotations=[
                Annotation(
                    analytic="test_analytic",
                    type="opinion",
                    value="malicious",
                    confidence=0.9,
                    summary="Test annotation with non-serializable raw data",
                )
            ],
            raw_data=mock_requests_response,  # This is the problematic non-serializable object
        )

    plugin = CluePlugin(
        app_name="test_serialization_plugin",
        classification="TLP:CLEAR",
        supported_types={"ipv4", "domain"},
        enrich=enrich_with_bad_data,
        logger=logging.getLogger("test_serialization"),
        enable_cache=False,  # Disable cache to ensure we hit the enrich function
    )

    return plugin


@pytest.fixture
def plugin_with_custom_non_serializable():
    """Create a CluePlugin that returns QueryEntry with custom non-serializable object."""

    def enrich_with_custom_bad_data(type_name: str, value: str, params, token):
        """Enrich function that returns custom non-serializable data."""
        return QueryEntry(
            count=1,
            classification="TLP:CLEAR",
            annotations=[],
            raw_data=NonSerializableObject("test_data"),  # Custom non-serializable object
        )

    plugin = CluePlugin(
        app_name="test_custom_serialization",
        classification="TLP:CLEAR",
        supported_types={"ipv4"},
        enrich=enrich_with_custom_bad_data,
        logger=logging.getLogger("test_custom_serialization"),
        enable_cache=False,
    )

    return plugin


def test_single_lookup_with_non_serializable_response(plugin_with_non_serializable_response):
    """Test that single lookup with non-serializable raw_data returns 500 error."""
    plugin = plugin_with_non_serializable_response

    with plugin.app.test_request_context():
        client = plugin.app.test_client()
        response = client.get("/lookup/ipv4/192.168.1.1/")

        # Currently, this will fail with an unhandled exception
        # After fixing the implementation, it should return 500
        assert response.status_code == 500

        data = response.get_json()

        # Verify standard API response format is maintained
        assert "api_response" in data
        assert "api_error_message" in data
        assert "api_status_code" in data

        # Verify error message is user-friendly (not exposing internal details)
        error_msg = data["api_error_message"]
        assert error_msg is not None
        assert len(error_msg) > 0
        # Should contain some indication of serialization failure
        assert any(
            keyword in error_msg.lower() for keyword in ["serializ", "error", "convert", "json", "response"]
        ), f"Error message should mention serialization issue, got: {error_msg}"


def test_single_lookup_serialization_error_logging(plugin_with_non_serializable_response, caplog):
    """Test that serialization errors are properly logged with details."""
    plugin = plugin_with_non_serializable_response

    with caplog.at_level(logging.ERROR):
        with plugin.app.test_request_context():
            client = plugin.app.test_client()
            response = client.get("/lookup/ipv4/10.0.0.1/")

            # Verify response indicates error
            assert response.status_code == 500

    # Verify that an error/exception was logged
    assert len(caplog.records) > 0, "Expected error logging for serialization failure"

    # Find error/exception level logs
    error_logs = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert len(error_logs) > 0, "Expected at least one ERROR or EXCEPTION level log"

    # Verify the log contains details about the serialization issue
    log_messages = " ".join([record.message for record in error_logs])
    assert any(
        keyword in log_messages.lower() for keyword in ["serializ", "error", "exception", "dump", "json"]
    ), f"Error logs should mention serialization issue, got: {log_messages}"


def test_bulk_lookup_with_non_serializable_response(plugin_with_non_serializable_response):
    """Test that bulk lookup with non-serializable raw_data returns 500 error."""
    plugin = plugin_with_non_serializable_response

    with plugin.app.test_request_context():
        client = plugin.app.test_client()
        response = client.post(
            "/lookup/",
            json=[
                {"type": "ipv4", "value": "192.168.1.1"},
                {"type": "ipv4", "value": "10.0.0.1"},
            ],
        )

        # Should return 500 error
        assert response.status_code == 500

        data = response.get_json()

        # Verify standard API response format
        assert "api_response" in data
        assert "api_error_message" in data
        assert "api_status_code" in data

        # Verify error message indicates serialization issue
        error_msg = data["api_error_message"]
        assert error_msg is not None
        assert any(
            keyword in error_msg.lower() for keyword in ["serializ", "error", "convert", "json", "response"]
        ), f"Error message should mention serialization issue, got: {error_msg}"


def test_bulk_lookup_serialization_error_logging(plugin_with_non_serializable_response, caplog):
    """Test that bulk lookup serialization errors are properly logged."""
    plugin = plugin_with_non_serializable_response

    with caplog.at_level(logging.ERROR):
        with plugin.app.test_request_context():
            client = plugin.app.test_client()
            response = client.post(
                "/lookup/",
                json=[
                    {"type": "domain", "value": "example.com"},
                ],
            )

            assert response.status_code == 500

    # Verify error was logged
    error_logs = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert len(error_logs) > 0, "Expected error logging for bulk serialization failure"

    log_messages = " ".join([record.message for record in error_logs])
    assert any(
        keyword in log_messages.lower() for keyword in ["serializ", "error", "exception"]
    ), f"Error logs should mention serialization issue, got: {log_messages}"


def test_custom_non_serializable_object(plugin_with_custom_non_serializable):
    """Test handling of custom non-serializable objects (not just requests.Response)."""
    plugin = plugin_with_custom_non_serializable

    with plugin.app.test_request_context():
        client = plugin.app.test_client()
        response = client.get("/lookup/ipv4/8.8.8.8/")

        # Should return 500 error
        assert response.status_code == 500

        data = response.get_json()

        # Verify proper response structure
        assert "api_error_message" in data
        assert data["api_error_message"] is not None
        # Should not expose internal class names or implementation details
        # but should indicate a serialization/response error
        error_msg = data["api_error_message"].lower()
        assert "serializ" in error_msg or "error" in error_msg or "response" in error_msg


def test_response_format_consistency_on_serialization_error(plugin_with_non_serializable_response):
    """Test that error responses maintain consistent API format even during serialization failures."""
    plugin = plugin_with_non_serializable_response

    with plugin.app.test_request_context():
        client = plugin.app.test_client()
        response = client.get("/lookup/ipv4/172.16.0.1/")

        # Must be valid JSON
        data = response.get_json()
        assert data is not None, "Response should be valid JSON"

        # Must have all required API fields
        required_fields = ["api_response", "api_error_message", "api_status_code"]
        for field in required_fields:
            assert field in data, f"Response missing required field: {field}"

        # api_status_code should match HTTP status
        assert data["api_status_code"] == 500

        # Should have an error message
        assert data["api_error_message"] is not None
        assert len(data["api_error_message"]) > 0

        # api_response might be None or empty on error
        # (depending on implementation choice)


def test_serialization_error_does_not_expose_sensitive_data(plugin_with_non_serializable_response):
    """Test that serialization error messages don't expose sensitive internal data."""
    plugin = plugin_with_non_serializable_response

    with plugin.app.test_request_context():
        client = plugin.app.test_client()
        response = client.get("/lookup/ipv4/192.0.2.1/")

        data = response.get_json()
        error_msg = data.get("api_error_message", "").lower()

        # Should not contain internal implementation details
        sensitive_terms = [
            "traceback",
            "__dict__",
            "memory address",
            "0x",  # Memory addresses
            "file://",
            "/home/",  # File paths
            "password",
            "secret",
            "token",
        ]

        for term in sensitive_terms:
            assert term not in error_msg, f"Error message should not expose: {term}"

        # Should be a user-friendly message
        assert len(error_msg) < 500, "Error message should be concise, not a full traceback"
