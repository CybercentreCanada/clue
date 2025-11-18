import json
from typing import cast

from pydantic import BaseModel, ValidationInfo

from clue.common.exceptions import ClueValueError
from clue.common.logging import get_logger
from clue.models.results import DATA, FORMAT_MAPPINGS, FORMAT_MAPPINGS_REVERSE

logger = get_logger(__file__)


def validate_result(_format: str, data: DATA | None, info: ValidationInfo) -> DATA | None:  # noqa: C901
    "Validate a result in a model"
    if isinstance(data, BaseModel) and data.__class__ in FORMAT_MAPPINGS:
        expected_format = FORMAT_MAPPINGS[data.__class__]
        if expected_format != _format:
            raise ClueValueError(
                f"Format should be {expected_format} if data is of type {data.__class__.__name__}, "
                f"but is set to {_format}"
            )

    if _format in FORMAT_MAPPINGS_REVERSE and not any(
        isinstance(data, _type) for _type in FORMAT_MAPPINGS_REVERSE[_format]
    ):
        resolved = False
        for expected_type in FORMAT_MAPPINGS_REVERSE[_format]:
            if info.context and info.context.get("is_response", False) and issubclass(expected_type, BaseModel):
                data = cast(DATA, cast(BaseModel, expected_type).model_validate(data))
                resolved = True
            elif _format == "json" and isinstance(data, str):
                data = json.loads(data)
                resolved = True
            elif _format == "json" and isinstance(data, BaseModel):
                data = cast(DATA, data.model_dump(mode="json", exclude_none=True))
                resolved = True

            if resolved:
                break

        if not resolved:
            raise ClueValueError(
                f"data should be of type {getattr(expected_type, '__name__', str(expected_type))}, "
                f"but is set to {data.__class__.__name__}"
            )

    if _format == "graph" and isinstance(data, BaseModel):
        data = cast(DATA, data.model_dump(mode="json", exclude_none=True, by_alias=True))

    if _format == "json":
        try:
            json.dumps(data)
        except Exception:
            logger.exception("Exception on serialization")
            raise ClueValueError("Data is not JSON serializable, or is not valid JSON.")

    return data
