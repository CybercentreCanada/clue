from typing import override

from pydantic import Field

from clue.models.graph import BaseGraphModel, Metadata, Node
from clue.models.results.base import Result


class GraphResult(BaseGraphModel, Result):
    "A result describing a graph that should be returned"

    @override
    @staticmethod
    def format():
        "Return the clue format for this result"
        return "graph"

    id: str = Field(description="An ID for this generated graph.")
    metadata: Metadata = Metadata()
    data: list[list[Node]] = Field(
        description=(
            "A list of lists of nodes to render. The outer list breaks the nodes into columns, "
            "while the inner list breaks the nodes into rows."
        )
    )
    # related: dict[str, str] = Field(description="A dictionary of other related graphs.")
