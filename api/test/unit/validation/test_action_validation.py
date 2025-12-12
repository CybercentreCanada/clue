import pytest
from pydantic import BaseModel, ValidationError
from pydantic_core import Url

from clue.models.actions import Action, ActionResult, ExecuteRequest
from clue.models.results.base import Result
from clue.models.results.image import ImageResult


class ActionParamsGood(ExecuteRequest):
    potato: int
    arg2: str


class ActionParamsNested(ExecuteRequest):
    arg1: int
    arg2: ActionParamsGood


def test_action_validator():
    Action[ActionParamsGood].model_validate(
        {
            "id": "test_action",
            "name": "Test Action",
            "supported_types": {"ip"},
            "classification": "TLP:CLEAR",
            "summary": "Example summary",
            "potato": 1,
            "arg2": "bleh",
        }
    )

    with pytest.raises(ValidationError):
        Action[ActionParamsGood].model_validate(
            {
                "id": "test_action, bad id",
                "supported_types": {"ip"},
                "classification": "TLP:CLEAR",
                "summary": "Example summary",
                "potato": 1,
                "arg2": "bleh",
            }
        )

    with pytest.raises(ValidationError):
        Action[ActionParamsGood].model_validate(
            {
                "id": "test_action",
                "supported_types": {"not a real type"},
                "classification": "TLP:CLEAR",
                "summary": "Example summary",
                "potato": "wiolololo",
                "arg2": "bleh",
            }
        )

    with pytest.raises(ValidationError):
        Action[ActionParamsNested].model_validate(
            {
                "id": "test_action",
                "name": "Test Action",
                "supported_types": {"ip"},
                "classification": "TLP:CLEAR",
                "summary": "Example summary",
            }
        )

    with pytest.raises(ValidationError):
        Action[BaseModel].model_validate(  # pyright: ignore[reportInvalidTypeArguments]
            {
                "id": "test_action",
                "name": "Test Action",
                "supported_types": {"ip"},
                "classification": "TLP:CLEAR",
                "summary": "Example summary",
            }
        )

    with pytest.raises(ValidationError):
        Action[ActionParamsGood].model_validate(
            {
                "id": "$%^ygbe5b6yh9889huni",
                "name": "Test Action",
                "supported_types": {"ip"},
                "classification": "TLP:CLEAR",
                "summary": "Example summary",
                "potato": 1,
                "arg2": "bleh",
            }
        )


def test_json_schema_params():
    Action.model_validate(
        {
            "accept_multiple": True,
            "action_icon": "codicon:terminal",
            "classification": "TLP:CLEAR",
            "extra_schema": {
                "allOf": [
                    {
                        "if": {
                            "allOf": [
                                {"properties": {"test": {"const": "example_stg"}}},
                                {
                                    "properties": {"bleh": {"const": True}},
                                    "required": ["bleh"],
                                },
                            ]
                        },
                        "then": {"required": ["existing_example_stg_retention"]},
                    },
                ],
                "required": ["test"],
            },
            "id": "retain",
            "name": "Retain Data to Example",
            "params": {
                "$defs": {
                    "Selector": {
                        "properties": {
                            "classification": {
                                "anyOf": [{"type": "string"}, {"type": "null"}],
                                "default": None,
                                "title": "Classification",
                            },
                            "type": {"title": "Type", "type": "string"},
                            "value": {"title": "Value", "type": "string"},
                        },
                        "required": ["type", "value"],
                        "title": "Selector",
                        "type": "object",
                    }
                },
                "properties": {
                    "test": {
                        "description": "test",
                        "enum": ["one", "two", "three"],
                        "order": 1,
                        "title": "Test",
                        "type": "string",
                    },
                    "test_2": {
                        "default": None,
                        "description": "Test 2",
                        "enum": [
                            "one",
                            "two",
                            "three",
                        ],
                        "order": 2,
                        "rule": {
                            "condition": {
                                "failWhenUndefined": True,
                                "schema": {"const": "one"},
                                "scope": "#/properties/test",
                            },
                            "effect": "SHOW",
                        },
                        "title": "Tester",
                        "type": "string",
                    },
                    "name": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                        "default": None,
                        "description": "Test Name",
                        "order": 5,
                        "rule": {
                            "condition": {
                                "schema": {"const": "two"},
                                "scope": "#/properties/test_2",
                            },
                            "effect": "HIDE",
                        },
                        "title": "Retention Name",
                    },
                    "selector": {
                        "anyOf": [{"$ref": "#/$defs/Selector"}, {"type": "null"}],
                        "default": None,
                        "description": "The selector to execute the action on.",
                    },
                    "selectors": {
                        "anyOf": [{"items": {"$ref": "#/$defs/Selector"}, "type": "array"}, {"type": "null"}],
                        "default": None,
                        "description": "The selectors to execute the action on.",
                        "title": "Selectors",
                    },
                },
                "required": ["test"],
                "title": "Blah",
                "type": "object",
            },
            "summary": "Test.",
            "supported_types": ["telemetry"],
        }
    )

    with pytest.raises(ValidationError):
        Action.model_validate(
            {
                "accept_multiple": True,
                "action_icon": "codicon:terminal",
                "classification": "TLP:CLEAR",
                "extra_schema": {
                    "allOf": [
                        {
                            "if": {
                                "allOf": [
                                    {"properties": {"test": {"const": "example_stg"}}},
                                    {
                                        "properties": {"bleh": {"const": True}},
                                        "required": ["bleh"],
                                    },
                                ]
                            },
                            "then": {"required": ["existing_example_stg_retention"]},
                        },
                    ],
                    "required": ["test"],
                },
                "id": "retain",
                "name": "Retain Data to Example",
                "params": {},
                "summary": "Test.",
                "supported_types": ["telemetry"],
            }
        )


class CustomJsonResult(Result):
    test: str

    @staticmethod
    def format() -> str:
        "Return the format of the result"
        return "json"


def test_action_result_validation():
    with pytest.raises(ValidationError) as err:
        ActionResult(outcome="success", summary="success")

    assert "set a format" in str(err)

    with pytest.raises(ValidationError) as err:
        ActionResult(outcome="success", summary="success", format="pivot", output="345e4f5gER%TGY$%G^%^$.'.'/.'/")

    assert "must be a Url." in str(err)

    with pytest.raises(ValidationError) as err:
        ActionResult(outcome="success", summary="success", format="json", output=Url("https://google.ca"))

    assert "You can only return a Url if format is set to pivot." in str(err)

    with pytest.raises(ValidationError) as err:
        ActionResult(
            outcome="success",
            summary="success",
            format="json",
            output=ImageResult(image="https://google.ca", alt="test"),
        )

    assert "Format should be image if data is of type ImageResult" in str(err)

    ActionResult(
        outcome="success",
        summary="success",
        format="json",
        output=CustomJsonResult(test="test"),
    )


def test_execute_request_context_field():
    """Test the context field in ExecuteRequest accepts arbitrary dictionaries"""
    # Test with context provided
    request = ExecuteRequest.model_validate(
        {
            "context": {"source": "ui", "user_id": 123, "nested": {"key": "value"}},
            "selector": {"type": "ip", "value": "127.0.0.1"},
        }
    )
    assert request.context is not None
    assert request.context["source"] == "ui"
    assert request.context["user_id"] == 123
    assert request.context["nested"]["key"] == "value"

    # Test without context (should default to None)
    request_no_context = ExecuteRequest.model_validate({"selector": {"type": "ip", "value": "127.0.0.1"}})
    assert request_no_context.context is None

    # Test with empty context dictionary
    request_empty = ExecuteRequest.model_validate({"context": {}, "selector": {"type": "ip", "value": "127.0.0.1"}})
    assert request_empty.context == {}

    # Test context in subclass
    request_subclass = ActionParamsGood.model_validate(
        {
            "context": {"origin": "test", "metadata": {"version": "1.0"}},
            "selector": {"type": "domain", "value": "example.com"},
            "potato": 42,
            "arg2": "test_value",
        }
    )
    assert request_subclass.context is not None
    assert request_subclass.context["origin"] == "test"
    assert request_subclass.context["metadata"]["version"] == "1.0"
    assert request_subclass.potato == 42
    assert request_subclass.arg2 == "test_value"

    # Test that context can contain various types
    request_varied = ExecuteRequest.model_validate(
        {
            "context": {
                "string_val": "text",
                "int_val": 100,
                "float_val": 3.14,
                "bool_val": True,
                "list_val": [1, 2, 3],
                "null_val": None,
            },
            "selector": {"type": "sha256", "value": "a" * 64},
        }
    )

    assert request_varied.context is not None

    assert request_varied.context["string_val"] == "text"
    assert request_varied.context["int_val"] == 100
    assert request_varied.context["float_val"] == 3.14
    assert request_varied.context["bool_val"] is True
    assert request_varied.context["list_val"] == [1, 2, 3]
    assert request_varied.context["null_val"] is None
