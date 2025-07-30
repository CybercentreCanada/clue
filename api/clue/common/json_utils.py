import json
from typing import Any


def try_parse_json(json_str: str, return_raw: bool = False) -> dict[str, Any] | str | None:
    "Try and parse JSON, optionally returning the raw string if json loading fails."
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return json_str if return_raw else None
