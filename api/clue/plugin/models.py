from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from clue.models.network import QueryEntry


class BulkEntry(BaseModel):
    "Bulk plugin response for selectors"

    error: str | None = Field(
        description="Error message returned by plugin",
        default=None,
        examples=["An error occurred when enriching the data.", None],
    )
    items: list[QueryEntry] = Field(description="List of results from the plugin", default=[])
    raw_data: Any | None = Field(default=None, description="The raw data for the given results")

    model_config = ConfigDict(validate_assignment=True)
