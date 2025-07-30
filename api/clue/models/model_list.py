from typing import Any

from pydantic import BaseModel

from clue.models.actions import Action, ActionBase, ActionResult, ActionSpec, ExecuteRequest
from clue.models.fetchers import FetcherDefinition, FetcherResult
from clue.models.graph import (
    BaseGraphModel,
    Comparator,
    DisplayConfig,
    DisplayField,
    Metadata,
    Node,
    NodeColor,
    Style,
    VisualConfig,
)
from clue.models.network import Annotation, ClueResponse, QueryEntry, QueryResult
from clue.models.results.graph import GraphResult
from clue.models.results.image import ImageResult
from clue.models.selector import Selector

__MODEL_LIST: list[type[BaseModel]] = [
    Action,
    ActionBase,
    ActionResult,
    ActionSpec,
    ExecuteRequest,
    FetcherDefinition,
    ImageResult,
    FetcherResult,
    BaseGraphModel,
    Comparator,
    DisplayConfig,
    DisplayField,
    GraphResult,
    Metadata,
    Node,
    NodeColor,
    Style,
    VisualConfig,
    ClueResponse,
    Annotation,
    QueryEntry,
    QueryResult,
    Selector,
]

MODEL_SCHEMAS: dict[str, dict[str, Any]] = {}

for __model in __MODEL_LIST:
    MODEL_SCHEMAS[__model.__name__] = __model.model_json_schema()
