import os
import re
from typing import Self

from pydantic import BaseModel, Field, model_validator
from pydantic_core import Url

from clue.common.exceptions import ClueValueError
from clue.common.logging import get_logger
from clue.models.results.base import Result

logger = get_logger(__file__)


class StatusLabel(BaseModel):
    "Labels for the status, tied to s specific localization"

    language: str = Field(description="Localization language for this label (i.e., en, fr)")
    label: str = Field(description="The localized label text.")


class StatusResult(Result):
    "Information about the status of a selector"

    @staticmethod
    def format():
        "Return the clue format for this result"
        return "status"

    empty: bool = Field(
        description="Is this status empty (i.e., if there's no applicable status result)?", default=False
    )
    labels: list[StatusLabel] = Field(description="A list of status labels in various languages", default=[])
    link: Url | None = Field(description="An optional link for more information", default=None)
    icon: str | None = Field(description="An optional icon to style the status", default=None)
    color: str | None = Field(description="An optional hexadecimal colour to style the status", default=None)

    @model_validator(mode="after")
    def validate_model(self: Self) -> Self:
        "Ensure the model has correct localizations, and the color is a valid hex string"
        if self.empty:
            return self

        for language in os.environ.get("LOCALIZATION_LANGUAGES", "en,fr").split(","):
            if not language:
                continue

            if not any(label.language == language for label in self.labels):
                raise ClueValueError(f"Status is missing a localized result for the localization '{language}'")

        if self.color:
            if not re.match(r"^#[0-9a-f]{6}$", self.color, re.IGNORECASE):
                raise ClueValueError("Invalid hex color value provided. Shorthand colors are not supported.")

        return self
