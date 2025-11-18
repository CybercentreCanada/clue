import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from clue.models.graph import VisualConfig
from clue.models.results.graph import GraphResult


def read_graph(graph_name: str):
    return json.loads((Path(__file__).parent.parent.parent / "graphs" / f"{graph_name}.json").read_text())


@pytest.mark.parametrize(
    "graph,result",
    [
        ("process", "success"),
        ("process_snake_case", "success"),
        ("process_vertical", "success"),
        ("tree", "success"),
        ("missing_metadata", "success"),
        ("extra_config", "error"),
        ("missing_id", "error"),
        ("missing_data", "error"),
    ],
)
def test_basic_validation(graph, result):
    if result == "success":
        GraphResult.model_validate(read_graph(graph))
    else:
        with pytest.raises(ValidationError):
            GraphResult.model_validate(read_graph(graph))


def test_graph_validator():
    process_data = GraphResult.model_validate(read_graph("process"))
    assert len(process_data.data) == 9
    assert len(process_data.metadata.display.display_field) == 1
    assert process_data.metadata.display.display_field[0].label == "filename"

    process_snake_case_data = GraphResult.model_validate(read_graph("process_snake_case"))
    assert len(process_snake_case_data.data) == 9
    assert len(process_snake_case_data.metadata.display.display_field) == 1
    assert process_snake_case_data.metadata.display.display_field[0].label == "filename"

    process_vertical_data = GraphResult.model_validate(read_graph("process_vertical"))
    assert len(process_vertical_data.data) == 9
    assert len(process_vertical_data.metadata.display.display_field) == 2
    assert str(process_vertical_data.metadata.display.display_field[1].operator) == ">"

    tree_data = GraphResult.model_validate(read_graph("tree"))
    assert len(tree_data.data) == 7
    assert len(tree_data.data[6]) == 6
    assert len(tree_data.data[6][0].edges) == 0
    assert tree_data.data[6][0].id == "Andromache"


def test_row_step_multiplier():
    assert VisualConfig(y_spacing=16).row_step == 32
    assert VisualConfig(ySpacing=14).row_step == 28

    assert VisualConfig(**{"y_spacing": 10}).row_step == 20  # noqa: PIE804
    assert VisualConfig(**{"ySpacing": 10}).row_step == 20  # noqa: PIE804
