# ruff: noqa: D101
from typing import Any, TypeVar

from pydantic import BaseModel

from clue.models.results.base import Result
from clue.models.results.graph import GraphResult
from clue.models.results.image import ImageResult
from clue.models.results.status import StatusResult

DATA = TypeVar("DATA", bound=(dict[str, Any] | list[dict[str, Any]] | str | Result))

FORMAT_MAPPINGS: dict[type[BaseModel] | type[dict] | type[list] | type[str], str] = {
    dict: "json",
    list: "json",
    str: "markdown",
    ImageResult: ImageResult.format(),
    StatusResult: StatusResult.format(),
    GraphResult: GraphResult.format(),
}
FORMAT_MAPPINGS_REVERSE: dict[str, list[type[BaseModel] | type[dict] | type[list] | type[str]]] = {}

for k, v in FORMAT_MAPPINGS.items():
    if v not in FORMAT_MAPPINGS_REVERSE:
        FORMAT_MAPPINGS_REVERSE[v] = [k]
    else:
        FORMAT_MAPPINGS_REVERSE[v].append(k)


def register_result(model: type[Result]):
    "Add a new result type to the mappings"
    if model.format() not in FORMAT_MAPPINGS_REVERSE:
        FORMAT_MAPPINGS[model] = model.format()
        FORMAT_MAPPINGS_REVERSE[model.format()] = [model]
