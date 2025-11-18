# ruff: noqa: D101
import re
from typing import Dict, Generic, Literal, Optional, Self, Union

from pydantic import (
    BaseModel,
    Field,
    JsonValue,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_core import Url

from clue.common.exceptions import ClueValueError
from clue.common.logging import get_logger
from clue.constants.supported_types import SUPPORTED_TYPES
from clue.models.results import DATA, FORMAT_MAPPINGS_REVERSE
from clue.models.results.validation import validate_result
from clue.models.validators import validate_classification

logger = get_logger(__file__)


class FetcherDefinition(BaseModel):
    id: str = Field(description="An ID for the given fetcher. Structured as <plugin_id>.<fetcher_id>.")
    classification: str = Field(
        description="Classification of the fetcher. Denotes the maximum classification of data sent to the fetcher.",
    )
    description: str = Field(description="A basic description of the fetcher's usage.")
    format: str = Field(description="The output format of the fetcher's result.")
    supported_types: set[str] = Field(description="A list of types this fetcher supports.")
    extra_data: Optional[Dict[str, JsonValue]] = Field(
        default=None, description="Extra data you want to define for a fetcher"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, fetcher_id: str) -> str:  # noqa: ANN102
        """Validates the fetcher ID field.

        Args:
            fetcher_id (str): The ID to validate.

        Raises:
            ClueValueError: Raised whenever the ID is not in a valid format.

        Returns:
            str: The validated ID.
        """
        if re.match(r"[^a-z_]", fetcher_id):
            raise ClueValueError("Invalid fetcher id - can only contain lowercase letters and underscores.")

        return fetcher_id

    @field_validator("classification")
    @classmethod
    def check_classification(cls, classification: str) -> str:  # noqa: ANN102
        """Validates the provided classification.

        Args:
            classification (str): The classification to validate.

        Raises:
            AssertionError: Raised whenever the provided classification is not valid.

        Returns:
            str: The validated classification.
        """
        return validate_classification(classification)

    @field_validator("format")
    @classmethod
    def check_format(cls, format: str) -> str:  # noqa: ANN102
        """Validates the provided format.

        Args:
            format (str): The format to validate.

        Raises:
            ClueValueError: Raised whenever the provided format is not valid.

        Returns:
            str: The validated classification.
        """
        if format not in FORMAT_MAPPINGS_REVERSE:
            raise ClueValueError("Invalid format. To use custom results, register your result using register_result.")

        return format

    @field_validator("supported_types")
    @classmethod
    def validate_supported_types(cls, supported_types: set[str]) -> set[str]:  # noqa: ANN102
        """Validate that the list of supported types matches the list of supported types"""
        invalid_types = supported_types - set(SUPPORTED_TYPES.keys())

        if invalid_types:
            logger.warning(f"{', '.join(invalid_types)} are not supported types - you may have a typo!")

        return supported_types


class FetcherResult(BaseModel, Generic[DATA]):
    outcome: Union[Literal["success"], Literal["failure"]] = Field(description="Did the fetcher succeed or fail?")
    data: DATA | None = Field(description="The output of the fetcher.", default=None)
    error: str | None = Field(description="If the fetcher failed, contains the relevant error message.", default=None)
    format: str = Field(
        description="What is the format of the output? Used to indicate what component to use when rendering "
        "the output.",
    )
    link: Optional[Url] = Field(description="Link to more information on the fetcher", default=None)

    @model_validator(mode="after")
    def validate_model(self: Self, info: ValidationInfo) -> Self:  # noqa: C901
        """Validates the entire model.

        Raises:
            AssertionError: Raised whenever a field is invalid on the model.

        Returns:
            Self: The validated model.
        """
        if self.outcome == "success" and self.data is None:
            raise ClueValueError("Successful fetcher results must return data.")

        if self.outcome == "failure":
            if self.data is not None:
                raise ClueValueError("Failed fetcher results cannot return data.")
            elif self.format != "error" or not self.error:
                raise ClueValueError("Returning an error fetcher result must specify an error.")
            else:
                return self
        elif self.error:
            raise ClueValueError("Errors can only be specified if the outcome is failure.")

        self.data = validate_result(self.format, self.data, info)

        return self

    @staticmethod
    def error_result(err: str) -> "FetcherResult":
        "Helper function to generate a failed fetcher result"
        return FetcherResult(outcome="failure", format="error", error=err)
