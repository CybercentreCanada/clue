import pytest
from pydantic import BaseModel, Field, ValidationError
from pydantic_core import Url

from clue.models.actions import (
    Action,
    ActionContextInformation,
    ActionResult,
    ExecuteRequest,
)
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
    assert request.context.model_extra is not None
    assert request.context.model_extra["source"] == "ui"
    assert request.context.model_extra["user_id"] == 123
    assert request.context.model_extra["nested"]["key"] == "value"

    # Test without context (should default to None)
    request_no_context = ExecuteRequest.model_validate({"selector": {"type": "ip", "value": "127.0.0.1"}})
    assert request_no_context.context is None

    # Test with empty context dictionary
    request_empty = ExecuteRequest.model_validate({"context": {}, "selector": {"type": "ip", "value": "127.0.0.1"}})
    assert request_empty.context is not None
    assert request_empty.context.model_dump(mode="json", exclude_unset=True) == {}

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
    assert request_subclass.context.model_extra is not None
    assert request_subclass.context.model_extra["origin"] == "test"
    assert request_subclass.context.model_extra["metadata"]["version"] == "1.0"
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

    assert request_varied.context.model_extra is not None
    assert request_varied.context.model_extra["string_val"] == "text"
    assert request_varied.context.model_extra["int_val"] == 100
    assert request_varied.context.model_extra["float_val"] == 3.14
    assert request_varied.context.model_extra["bool_val"] is True
    assert request_varied.context.model_extra["list_val"] == [1, 2, 3]
    assert request_varied.context.model_extra["null_val"] is None


def test_action_context_information_basic():
    """Test basic ActionContextInformation functionality"""
    # Test with known fields
    context = ActionContextInformation(
        url="https://example.com/investigation/123", timestamp="2024-01-01T12:00:00Z", language="en"
    )
    assert context.url == "https://example.com/investigation/123"
    assert context.timestamp == "2024-01-01T12:00:00Z"
    assert context.language == "en"

    # Test with arbitrary fields (extra="allow")
    context_with_extras = ActionContextInformation.model_validate(
        {
            "url": "https://example.com",
            "timestamp": "2024-12-15T10:30:00Z",
            "language": "fr",
            "custom_field": "custom_value",
            "user_id": 42,
            "metadata": {"version": "1.0"},
        }
    )
    assert context_with_extras.url == "https://example.com"
    assert context_with_extras.timestamp == "2024-12-15T10:30:00Z"
    assert context_with_extras.language == "fr"
    assert context_with_extras.model_extra is not None
    assert context_with_extras.model_extra["custom_field"] == "custom_value"
    assert context_with_extras.model_extra["user_id"] == 42
    assert context_with_extras.model_extra["metadata"]["version"] == "1.0"

    # Test with only some known fields
    partial_context = ActionContextInformation(url="https://example.com")
    assert partial_context.url == "https://example.com"
    assert partial_context.timestamp is None
    assert partial_context.language is None

    # Test with empty context
    empty_context = ActionContextInformation()
    assert empty_context.url is None
    assert empty_context.timestamp is None
    assert empty_context.language is None


def test_action_context_information_coerce_to():
    """Test the coerce_to method for converting context to subclasses"""

    # Define a custom context subclass
    class CustomContext(ActionContextInformation):
        source: str | None = Field(default=None, description="Source of the action")
        user_id: int | None = Field(default=None, description="User ID")

    # Create a base context with known fields and extra fields
    base_context = ActionContextInformation.model_validate(
        {
            "url": "https://example.com/case/456",
            "timestamp": "2024-12-15T14:00:00Z",
            "language": "en",
            "source": "ui",
            "user_id": 123,
            "additional_field": "extra_value",
        }
    )

    # Coerce to custom context
    custom_context = base_context.coerce_to(CustomContext)

    # Verify it's the correct type
    assert isinstance(custom_context, CustomContext)
    assert isinstance(custom_context, ActionContextInformation)

    # Verify known fields are preserved
    assert custom_context.url == "https://example.com/case/456"
    assert custom_context.timestamp == "2024-12-15T14:00:00Z"
    assert custom_context.language == "en"

    # Verify custom fields are now properly typed
    assert custom_context.source == "ui"
    assert custom_context.user_id == 123

    # Verify extra fields are still preserved
    assert custom_context.model_extra is not None
    assert custom_context.model_extra["additional_field"] == "extra_value"


def test_action_context_information_coerce_to_with_validation():
    """Test that coerce_to properly validates the target subclass"""

    # Define a subclass with required fields
    class StrictContext(ActionContextInformation):
        required_field: str
        optional_field: str | None = None

    # Create a base context with the required field
    base_context = ActionContextInformation.model_validate(
        {"url": "https://example.com", "required_field": "value", "optional_field": "optional"}
    )

    # Should successfully coerce
    strict_context = base_context.coerce_to(StrictContext)
    assert strict_context.required_field == "value"
    assert strict_context.optional_field == "optional"
    assert strict_context.url == "https://example.com"

    # Create a base context WITHOUT the required field
    base_context_invalid = ActionContextInformation.model_validate({"url": "https://example.com"})

    # Should raise ValidationError when coercing
    with pytest.raises(ValidationError) as err:
        base_context_invalid.coerce_to(StrictContext)

    assert "required_field" in str(err.value)


def test_action_context_information_coerce_to_preserves_none():
    """Test that coerce_to preserves None values for known fields"""

    class ExtendedContext(ActionContextInformation):
        custom_field: str | None = None

    # Create context with explicit None values
    base_context = ActionContextInformation(url="https://example.com", timestamp=None, language=None)

    extended_context = base_context.coerce_to(ExtendedContext)

    assert extended_context.url == "https://example.com"
    assert extended_context.timestamp is None
    assert extended_context.language is None
    assert extended_context.custom_field is None


def test_execute_request_with_typed_context():
    """Test ExecuteRequest with ActionContextInformation"""
    request = ExecuteRequest.model_validate(
        {
            "context": {"url": "https://example.com", "timestamp": "2024-12-15T10:00:00Z", "custom_key": "value"},
            "selector": {"type": "ip", "value": "127.0.0.1"},
        }
    )

    assert request.context is not None
    assert isinstance(request.context, ActionContextInformation)
    assert request.context.url == "https://example.com"
    assert request.context.timestamp == "2024-12-15T10:00:00Z"
    assert request.context.language is None
    assert request.context.model_extra is not None
    assert request.context.model_extra["custom_key"] == "value"
