import inspect
import re
from functools import wraps
from typing import Any, Callable, Optional, cast

from flasgger import utils
from pydantic import TypeAdapter

from clue.models.network import (
    Annotation,
    ClueResponse,
    QueryEntry,
    QueryResult,
)
from clue.services import type_service


def monkey_patched_parse(obj: object, *args: tuple[Any], **kwargs) -> tuple[Optional[str], Optional[str], None]:
    """Parse existing docstrings for a python object and return a short and long description of it

    Args:
        obj (object): The object to inspect.

    Returns:
        tuple[str, str, None]: A tuple containing the short and long description, along with a None just for fun
            (i've got no idea why).
    """
    short_desc: Optional[str] = None
    long_desc: Optional[str] = None

    doc = inspect.getdoc(obj)

    if doc:
        short_desc = doc.splitlines()[0]
        long_desc = f"```\n{doc}\n```"

    return short_desc, long_desc, None


utils.parse_docstring = monkey_patched_parse

DEFINITIONS = {
    "QueryResult": QueryResult.model_json_schema(ref_template="#/definitions/{model}"),
    "QueryEntry": QueryEntry.model_json_schema(ref_template="#/definitions/{model}"),
    "Annotation": Annotation.model_json_schema(ref_template="#/definitions/{model}"),
}

RESPONSES = {
    status_code: {
        "description": "Something went wrong with your request",
        "schema": {
            **ClueResponse.model_json_schema(),
            "example": ClueResponse(error_message="Example error", status_code=status_code).model_dump(),
        },
    }
    for status_code in [400, 401, 403, 404]
}


def generate_swagger_docs(responses: dict[int, str] = {}) -> Callable:  # noqa: C901
    """Generates a decorator that allows to create swagger doc for an endpoint.

    Args:
        responses (dict[int, str], optional): A dict of the possible responses, with the HTTP code as the key and the
            description of the response as the value. Defaults to {}.

    Returns:
        Callable: The decorator
    """

    def decorator(function: Callable) -> Callable:
        func_signature = inspect.signature(function)
        func_doc = inspect.getdoc(function)
        if module := inspect.getmodule(function):
            module_name = module.__name__
        func_path = f"{module_name}.{function.__name__}" if module_name else function.__name__

        path_params = [
            {
                "name": param,
                "in": "path",
                "type": "string",
                "enum": list(type_service.SUPPORTED_TYPES.keys()) if param == "type_name" else None,
            }
            for param in func_signature.parameters
            if param not in ["kwargs", "_"] and not param.startswith("_")
        ]

        query_params: list[dict[str, Any]] = []
        if func_doc:
            for section in func_doc.split("\n\n"):
                lines = section.splitlines()
                if not lines[0].lower().endswith("arguments:"):
                    continue

                lines = [re.sub(r" =>.+", "", line).strip() for line in lines[1:]]

                for line in lines:
                    if line.lower() == "none" or "=>" not in line:
                        continue

                    if ": " in line:
                        name, type = line.split(": ")
                    else:
                        name = line
                        type = None

                    query_params.append({"name": name, "in": "query", "type": type})

        tags: list[str] = []
        if module := inspect.getmodule(function):
            tags.append(module.__name__.split(".")[-1].capitalize())

        cast(Any, function).specs_dict = {
            "parameters": [*path_params, *query_params],
            "definitions": DEFINITIONS,
            "responses": {
                "200": {
                    "description": responses.get(200, "Request succeeded"),
                    "schema": (
                        TypeAdapter(func_signature.return_annotation).json_schema(ref_template="#/definitions/{model}")
                        if func_signature.return_annotation != inspect._empty
                        else None
                    ),
                },
                **RESPONSES,
            },
            "summary": "test",
            "tags": tags,
            "operationId": func_path,
        }

        @wraps(function)
        def wrapper(*args, **kwargs):
            return function(*args, **kwargs)

        return wrapper

    return decorator
