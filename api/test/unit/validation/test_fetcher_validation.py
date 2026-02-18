import pytest
from pydantic import ValidationError

from clue.models.fetchers import (
    FetcherDefinition,
    FetcherResult,
)
from clue.models.results import FORMAT_MAPPINGS, FORMAT_MAPPINGS_REVERSE, register_result
from clue.models.results.base import Result
from clue.models.results.file import FileResult
from clue.models.results.image import ImageResult
from clue.models.results.status import StatusLabel, StatusResult


class TestFetcherDefinition:
    """Tests for FetcherDefinition validation behavior."""

    def test_fetcher_definition_valid(self):
        """Test FetcherDefinition accepts valid fields."""
        FetcherDefinition(
            id="test_definition",
            classification="TLP:CLEAR",
            description="test",
            format="image",
            supported_types={"ip"},
        )

    def test_fetcher_definition_invalid_id(self):
        """Test FetcherDefinition rejects invalid fetcher IDs."""
        with pytest.raises(ValidationError):
            FetcherDefinition(
                id="%^RG&$%^BYSDRFTG",
                classification="TLP:CLEAR",
                description="test",
                format="image",
                supported_types={"ip"},
            )


class TestFetcherResultValidation:
    """Basic validation tests for FetcherResult semantics."""

    def test_success_requires_data(self):
        """Test success results require data."""
        with pytest.raises(ValidationError):
            FetcherResult(outcome="success", format="image", data=None)

        with pytest.raises(ValidationError):
            FetcherResult(outcome="success", format="json", data=None)

    def test_failure_rejects_data(self):
        """Test failure results cannot include data."""
        with pytest.raises(ValidationError):
            FetcherResult(outcome="failure", format="image", data={})

        with pytest.raises(ValidationError):
            FetcherResult(outcome="failure", format="json", data={})

    def test_failure_requires_error_format_and_message(self):
        """Test failure results require format=error and a non-empty error message."""
        with pytest.raises(ValidationError):
            FetcherResult(outcome="failure", format="error")

        with pytest.raises(ValidationError):
            FetcherResult(outcome="failure", format="json", error="bad request")

    def test_success_rejects_error_message(self):
        """Test success results cannot include an error message."""
        with pytest.raises(ValidationError):
            FetcherResult(outcome="success", format="json", data={"ok": True}, error="not allowed")

    def test_error_result_helper(self):
        """Test the helper for generating a failed fetcher result."""
        result = FetcherResult.error_result("sample error")

        assert result.outcome == "failure"
        assert result.format == "error"
        assert result.error == "sample error"
        assert result.data is None


class TestImageFetcherResult:
    """Validation tests for image fetcher results."""

    def test_image_result_valid(self):
        """Test valid image data is accepted."""
        FetcherResult(
            outcome="success", format="image", data=ImageResult(image="http://example.com", alt="Example Alt Text")
        )

    def test_image_result_invalid_payload(self):
        """Test image format rejects incompatible payloads."""
        with pytest.raises(ValidationError):
            FetcherResult(outcome="success", format="image", data={"potato": "test"})

        with pytest.raises(ValidationError):
            FetcherResult(outcome="success", format="image")


class TestJsonFetcherResult:
    """Validation tests for json fetcher results."""

    def test_json_result_valid(self):
        """Test valid JSON-like payload is accepted."""
        FetcherResult(outcome="success", format="json", data={"literally": "anything"})

    def test_json_result_invalid_payload(self):
        """Test json format rejects malformed or unserializable payloads."""
        with pytest.raises(ValidationError):
            FetcherResult(outcome="success", format="json", data='{"literally": "anything"')

        with pytest.raises(ValidationError):
            FetcherResult(outcome="success", format="json", data={"bad": lambda x: "potato"})


class TestStatusFetcherResult:
    """Validation tests for status result model behavior."""

    def test_status_result_validation(self, monkeypatch):
        """Test status validation under different localization settings."""
        with monkeypatch.context() as m:
            m.setenv("LOCALIZATION_LANGUAGES", "")
            StatusResult(labels=[])

            m.setenv("LOCALIZATION_LANGUAGES", "en")
            StatusResult(labels=[StatusLabel(language="en", label="test")])
            with pytest.raises(ValidationError):
                StatusResult(labels=[])

            m.setenv("LOCALIZATION_LANGUAGES", "")
            StatusResult(labels=[], color="#000000")

            with pytest.raises(ValidationError):
                StatusResult(labels=[], color="bad color")


class TestFileResult:
    """Tests for FileResult model validation and functionality."""

    def test_file_result_format(self):
        """Test that FileResult returns correct format."""
        assert FileResult.format() == "file"

    def test_file_result_valid_minimal(self):
        """Test FileResult with minimal required fields."""
        result = FileResult(data="aGVsbG8gd29ybGQ=")
        assert result.data == "aGVsbG8gd29ybGQ="
        assert result.mime_type == "application/octet-stream"
        assert result.file_name is None

    def test_file_result_valid_all_fields(self):
        """Test FileResult with all fields populated."""
        result = FileResult(
            data="aGVsbG8gd29ybGQ=",
            mime_type="text/plain",
            file_name="test.txt",
        )
        assert result.data == "aGVsbG8gd29ybGQ="
        assert result.mime_type == "text/plain"
        assert result.file_name == "test.txt"

    def test_file_result_custom_mime_type(self):
        """Test FileResult with custom mime type."""
        result = FileResult(
            data="Ym9vYg==",
            mime_type="application/json",
            file_name="data.json",
        )
        assert result.mime_type == "application/json"

    def test_file_result_missing_data(self):
        """Test FileResult validation fails when data is missing."""
        with pytest.raises(ValidationError) as exc_info:
            FileResult()  # pyright: ignore[reportCallIssue]
        assert "data" in str(exc_info.value)

    def test_file_result_data_not_string(self):
        """Test FileResult validation fails when data is not a string."""
        with pytest.raises(ValidationError) as exc_info:
            FileResult(data=12345)  # pyright: ignore[reportArgumentType]
        assert "data" in str(exc_info.value)

    def test_file_result_file_name_empty_string(self):
        """Test FileResult with empty string file name."""
        result = FileResult(data="dGVzdA==", file_name="")
        assert result.file_name == ""

    def test_fetcher_validation_file(self):
        """Test FileResult validation for use in fetcher context."""
        file_result = FileResult(
            data="aGVsbG8gd29ybGQ=",
            mime_type="text/plain",
            file_name="example.txt",
        )
        assert file_result.format() == "file"
        assert file_result.data == "aGVsbG8gd29ybGQ="
        assert file_result.mime_type == "text/plain"
        assert file_result.file_name == "example.txt"


class ExampleResult(Result):
    @staticmethod
    def format():
        return "example"

    hello: str


def test_register_result():
    with pytest.raises(ValidationError):
        FetcherDefinition(
            id="preview",
            format="example",
            classification="TLP:CLEAR",
            description="example thing",
            supported_types={"sha256"},
        )

    register_result(ExampleResult)

    assert "example" in FORMAT_MAPPINGS_REVERSE
    assert FORMAT_MAPPINGS[ExampleResult] == "example"
