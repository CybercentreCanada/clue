# ruff: noqa: D101
import re
from inspect import isclass
from typing import (
    Any,
    Generic,
    Literal,
    Self,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator
from pydantic_core import Url, ValidationError

from clue.common.exceptions import ClueValueError
from clue.common.logging import get_logger
from clue.constants.supported_types import SUPPORTED_TYPES
from clue.models.results import DATA
from clue.models.results.validation import validate_result
from clue.models.selector import Selector
from clue.models.validators import validate_classification

logger = get_logger(__file__)


class ExecuteRequest(BaseModel):
    selector: Selector | None = Field(description="The selector to execute the action on.", default=None)
    selectors: list[Selector] = Field(description="The selectors to execute the action on.", default=[])

    @model_validator(mode="after")
    def validate_model(self: Self, info: ValidationInfo) -> Self:  # noqa: C901
        """Validates the entire model.

        Raises:
            AssertionError: Raised whenever a field is invalid on the model.

        Returns:
            Self: The validated model.
        """
        action_to_validate: Action | None = None
        if info.context:
            action_to_validate: Action | None = info.context.get("action", None)

        if self.selector is None and (self.selectors is None or len(self.selectors) < 1):
            if not action_to_validate or not action_to_validate.accept_empty:
                raise ClueValueError(
                    "Either selector (single entry) or selectors (multiple entries) must not be empty."
                )
        elif self.selectors is None or len(self.selectors) < 1:
            self.selectors = [cast(Selector, self.selector)]
        elif self.selector is None and len(self.selectors) == 1:
            self.selector = self.selectors[0]

        return self


ER = TypeVar("ER", bound=ExecuteRequest)


class ActionBase(BaseModel):
    id: str = Field(description="Unique identifier for the action.")
    name: str = Field(description="Name of the action.")
    classification: str = Field(
        description="Classification of the action. Denotes the maximum classification of data sent to the action.",
    )
    summary: str | None = Field(description="A plaintext summary of the action.", default=None)
    supported_types: set[str] = Field(description="A list of types this action supports.")
    action_icon: str | None = Field(
        description=(
            "Formatted string to present an icon for this analytic on the UI using iconify/react format: "
            "https://iconify.design/docs/icon-components/react/. External icons not yet supported."
        ),
        default=None,
    )
    accept_empty: bool = Field(description="Does this action support execution with no selectors?", default=False)
    accept_multiple: bool = Field(description="Does this action support multiple values?", default=False)
    format: str | None = Field(
        description="What is the format of the output, if known?",
        default=None,
    )
    extra_schema: Any | None = Field(
        description="Extra key values for the form schema. These will overwrite default behaviour", default={}
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, action_id: str) -> str:  # noqa: ANN102
        """Validates the action ID field.

        Args:
            action_id (str): The ID to validate.

        Raises:
            ClueValueError: Raised whenever the ID is not in a valid format.

        Returns:
            str: The validated ID.
        """
        if re.match(r"[^a-z_]", action_id):
            raise ClueValueError("Invalid action id - can only contain lowercase letters and underscores.")

        return action_id

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

    @field_validator("supported_types")
    @classmethod
    def validate_supported_types(cls, supported_types: set[str]) -> set[str]:  # noqa: ANN102
        """Validate that the list of supported types matches the list of supported types"""
        invalid_types = supported_types - set(SUPPORTED_TYPES.keys())

        if invalid_types:
            logger.warning(f"{', '.join(invalid_types)} are not supported types - you may have a typo!")

        return supported_types


class Action(ActionBase, Generic[ER]):
    params: ER | dict[str, Any] | None = Field(description="Specification of additional parameters.", default=None)

    @model_validator(mode="before")
    @classmethod
    def check_structure(cls, data: Any) -> Any:  # noqa: ANN102
        """Checks the structure of the model.

        Args:
            data (Any): The model data to validate.

        Raises:
            ClueValueError: Raised whenever the additional_annotations field doesn't inherit ExecuteRequest
            AssertionError: Raised whenever a field is not valid.

        Returns:
            Any: The validated data.
        """
        additional_annotations: type[Any] = cast(type[Any], cls.model_fields["params"].annotation).__args__[0]

        if not isinstance(data.get("params", None), dict) and isinstance(additional_annotations, TypeVar):
            raise ClueValueError(
                "you must provide a non-generic class as a type annotation. To accept no additional parameters, use "
                "Action[ExecuteRequest]."
            )

        if isinstance(data.get("params", None), dict):
            if "$defs" not in data["params"]:
                raise ClueValueError("If params is a dict, it must be a valid json schema.")

            return data
        elif not issubclass(additional_annotations, ExecuteRequest):
            raise ClueValueError(
                "params does not inherit from ExecuteRequest. When extending the params, it is necessary to inherit "
                "from ExecuteRequest."
            )

        missing_annotations = [key for key, info in additional_annotations.model_fields.items() if not info.annotation]

        if missing_annotations:
            raise AssertionError(
                f"{','.join(missing_annotations)} do not have type annotations. All fields must be annotated"
            )

        nested_fields: list[str] = []
        for key, info in additional_annotations.model_fields.items():
            field_type = cast(type[Any], info.annotation)

            if get_origin(field_type) is Union:
                field_type = get_args(field_type)[0]

            if key not in ["selector", "selectors"] and isclass(field_type) and BaseModel in field_type.__mro__:
                nested_fields.append(key)

        if nested_fields:
            raise AssertionError(
                f"{','.join(nested_fields)} are not primitive types. params cannot require nested fields, "
                "except raw_data."
            )

        return data


class ActionResult(BaseModel, Generic[DATA]):
    outcome: Union[Literal["success"], Literal["failure"]] = Field(description="Did the action succeed or fail?")
    summary: str | None = Field(description="Message explaining the outcome of the action.", default=None)
    output: DATA | Url | None = Field(description="The output of the action.", default=None)
    format: str | None = Field(
        description="What is the format of the output? Used to indicate what component to use when rendering "
        "the output.",
        default=None,
    )
    link: Url | None = Field(description="Link to more information on the outcome of the action", default=None)

    @model_validator(mode="after")
    def validate_model(self: Self, info: ValidationInfo) -> Self:  # noqa: C901
        """Validates the entire model.

        Raises:
            AssertionError: Raised whenever a field is invalid on the model.

        Returns:
            Self: The validated model.
        """
        if not self.format and self.outcome != "failure":
            raise ClueValueError("You must set a format if outcome is not failure.")

        if self.format == "pivot" and (not self.output or not isinstance(self.output, Url)):
            if isinstance(self.output, str):
                try:
                    self.output = Url(self.output)
                    return self
                except ValidationError:
                    pass

            raise ClueValueError("When returning a pivot, output must be a Url.")

        if self.format != "pivot" and isinstance(self.output, Url):
            raise ClueValueError("You can only return a Url if format is set to pivot.")

        if self.format and not isinstance(self.output, Url):
            self.output = validate_result(self.format, self.output, info)

        return self


class ActionSpec(ActionBase):
    params: dict[str, Any]
