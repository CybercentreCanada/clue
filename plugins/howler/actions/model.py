from datetime import datetime

from clue.models.actions import ExecuteRequest
from clue.plugin import ClueValueError
from pydantic import Field, field_validator


class SearchPivotRequest(ExecuteRequest):
    "Specifies additional parameters for building the howler pivot"

    start_date: str | None = Field(description="Start of the time range (optional)", default=None)
    end_date: str | None = Field(description="End of the time range (optional)", default=None)

    @field_validator("start_date")
    @classmethod
    def validate_start_date(cls, start_date: str) -> str:  # noqa: ANN102
        """Validates the start_date field.

        Args:
            start_date (str): The date to validate.

        Raises:
            ClueValueError: Raised whenever the date is not a valid ISO format, and is not None.

        Returns:
            str: The validated start date.
        """
        if start_date is None:
            return start_date

        try:
            datetime.fromisoformat(start_date)
        except (TypeError, ValueError):
            raise ClueValueError("Invalid start date provided.")

        return start_date

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, end_date: str) -> str:  # noqa: ANN102
        """Validates the end_date field.

        Args:
            end_date (str): The date to validate.

        Raises:
            ClueValueError: Raised whenever the date is not a valid ISO format, and is not None.

        Returns:
            str: The validated end date.
        """
        if end_date is None:
            return end_date

        try:
            datetime.fromisoformat(end_date)
        except (TypeError, ValueError):
            raise ClueValueError("Invalid end date provided.")

        return end_date
