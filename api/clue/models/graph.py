# ruff: noqa: D101
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class BaseGraphModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class Operator(StrEnum):
    equals = "="
    less_than = "<"
    greater_than = ">"
    not_equals = "!="
    less_than_equal_to = "<="
    greater_than_equal_to = ">="
    includes = "~"


class Comparator(BaseGraphModel):
    field: str | None = Field(description="What field should the comparator check against?", default=None)
    operator: Operator | None = Field(
        description="What operation should the comparator use for this check?", default=None
    )
    value: str | int | bool | float | None = Field(
        description="What value should the comparator check the field against?", default=None
    )


class DisplayField(Comparator):
    zoom: float | None = Field(description="What zoom level should the field be shown at?", default=None)
    label: str = Field(description="What value should be shown from the node in this display field?")


class Type(StrEnum):
    node = "node"
    edge = "edge"


class Style(Comparator):
    color: str | None = Field(description="What colour should be applied to the matching elements?", default=None)
    size: float | None = Field(description="What size should the matching elements be?", default=None)
    type: Type = Field(description="What type of element do you want to select?")


class NodeColor(BaseGraphModel):
    border: str = Field(description="What default colour should the border of the nodes have?", default="grey")
    center: str = Field(description="What default colour should the center of the nodes have?", default="white")


class VisualConfig(BaseGraphModel):
    text_color: str = Field(description="What colour should the text on the graph be?", default="white")
    node_color: NodeColor = NodeColor()
    letter_size: float = Field(description="What size should the text on the graph be?", default=10)
    letter_width: float = Field(description="What size should the text on the graph be?", default=6.5)
    x_spacing: float = Field(description="How much spacing should there be between columns in the graph?", default=8)
    y_spacing: float = Field(description="How much spacing should there be between rows in the graph?", default=20)
    node_radius: float = Field(description="How large should nodes on the graph be?", default=6)
    max_arc_radius: float = Field(description="How gradual should curves of the edges of the graph be?", default=8)
    line_padding_x: float = Field(
        description="How much horizontal padding should there be between edges on the graph?", default=10
    )
    line_padding_y: float = Field(
        description="How much vertical padding should there be between edges on the graph?", default=10
    )
    line_width: float = Field(description="How thick should edges on the graph be?", default=3)
    enable_entry_padding: bool = Field(
        description="Should entries be separated by the length of the longest label?", default=True
    )
    truncate_labels: bool = Field(description="Should labels be truncated?", default=True)
    enable_timestamps: bool = Field(
        description="Should timestamps be enabled? This will also show annotations, if provided", default=True
    )
    icon_orientation: Optional[Literal["vertical"] | Literal["horizontal"]] = Field(
        description="Where should icons be rendered when provided - above or to the side of the node?",
        default="vertical",
    )
    line_direction: Optional[Literal["vertical"] | Literal["horizontal"]] = Field(
        description="What pathing behaviour should the edges of the graph use by default?",
        default="horizontal",
    )
    row_step: float = Field(
        description=(
            "How much spacing should there be between rows? This is calculated dynamically if not "
            "provided, based on y_spacing"
        ),
        default=0,
    )
    below_previous: bool = Field(
        description="Should each column be rendered below the previous?",
        default=False,
    )

    @model_validator(mode="before")
    @classmethod
    def prepare_model(cls, data: dict[str, Any]) -> dict[str, str]:  # noqa: ANN102
        """Calculates the row step if not provided.

        Args:
            data (dict[str, str]): The data to validate.

        Returns:
            dict[str, str]: The data including the password.
        """
        if "rowStep" not in data:
            if "ySpacing" in data:
                data["rowStep"] = 2 * data["ySpacing"]
            elif "y_spacing" in data:
                data["rowStep"] = 2 * data["y_spacing"]
            else:
                data["rowStep"] = 2 * VisualConfig.model_fields["y_spacing"].default

        return data


class Visualization(BaseGraphModel):
    config: VisualConfig = VisualConfig()
    type: Literal["tree"] | Literal["cloud"] = Field(
        description="The type of visualization to use. Defaults to tree", default="tree"
    )


class DisplayConfig(BaseGraphModel):
    display_field: list[DisplayField] = Field(description="A list of fields to present in the graph.", default=[])
    styles: list[Style] = Field(description="A list of styles to apply to the graph.", default=[])
    visualization: Visualization = Visualization()


class Node(BaseGraphModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(description="The ID of this node.")
    edges: list[str] = Field(description="A list of IDs this node connects to.", default=[])
    markdown: str | None = Field(
        description="A markdown string providing additional details on this node.", default=None
    )
    timestamp: datetime | None = Field(
        description="The timestamp associated with this node. Only rendered if enable_timestamps is set to true.",
        default=None,
    )
    annotation: str | None = Field(
        description="The annotation associated with this node. Only rendered if enable_timestamps is set to true.",
        default=None,
    )
    icons: list[str] = Field(description="A list of icons to show next to this node.", default=[])


class Metadata(BaseGraphModel):
    # TODO: Eventually support non-nested data
    type: Literal["nested"] = "nested"
    display: DisplayConfig = DisplayConfig()
    subgraphs: list[Comparator] = Field(
        description="A list of comparators used to automatically generate subgraphs in the fetcher.", default=[]
    )
