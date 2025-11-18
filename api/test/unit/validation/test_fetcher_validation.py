import pytest
from pydantic import ValidationError

from clue.models.fetchers import (
    FetcherDefinition,
    FetcherResult,
)
from clue.models.results import FORMAT_MAPPINGS, FORMAT_MAPPINGS_REVERSE, register_result
from clue.models.results.base import Result
from clue.models.results.image import ImageResult
from clue.models.results.status import StatusLabel, StatusResult


def test_fetcher_definition():
    FetcherDefinition(
        id="test_definition",
        classification="TLP:CLEAR",
        description="test",
        format="image",
        supported_types={"ip"},
    )

    with pytest.raises(ValidationError):
        FetcherDefinition(
            id="%^RG&$%^BYSDRFTG",
            classification="TLP:CLEAR",
            description="test",
            format="image",
            supported_types={"ip"},
        )


def test_fetcher_validation_on_success():
    "Setting data to None on success should throw a validation error"
    with pytest.raises(ValidationError):
        FetcherResult(outcome="success", format="image", data=None)

    with pytest.raises(ValidationError):
        FetcherResult(outcome="success", format="json", data=None)


def test_fetcher_validation_on_failure():
    "Not setting data to None on failure should throw a validation error"
    with pytest.raises(ValidationError):
        FetcherResult(outcome="failure", format="image", data={})

    with pytest.raises(ValidationError):
        FetcherResult(outcome="failure", format="json", data={})


def test_fetcher_validation_image():
    "Data must be an ImageResult when format is image"
    FetcherResult(
        outcome="success", format="image", data=ImageResult(image="http://example.com", alt="Example Alt Text")
    )

    with pytest.raises(ValidationError):
        FetcherResult(outcome="success", format="image", data={"potato": "test"})

    with pytest.raises(ValidationError):
        FetcherResult(outcome="success", format="image")


def test_fetcher_validation_json():
    "Data must be valid JSON (or serialize to valid JSON)"
    FetcherResult(outcome="success", format="json", data={"literally": "anything"})

    with pytest.raises(ValidationError):
        FetcherResult(outcome="success", format="json", data='{"literally": "anything"')

    with pytest.raises(ValidationError):
        FetcherResult(outcome="success", format="json", data={"bad": lambda x: "potato"})


def test_fetcher_validation_status(monkeypatch):
    "Data must be valid status"

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
