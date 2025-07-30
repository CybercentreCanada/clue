import random
from datetime import datetime
from typing import Union, get_args, get_origin

from pydantic import BaseModel
from pydantic_core import Url


def generate_example_model(model: type[BaseModel], as_list: bool = False):  # noqa: C901
    """Populate fields with example values"""
    result = {}

    if as_list:
        full_list = []
        for _ in range(random.randint(1, 3)):  # noqa: S311
            full_list.append(generate_example_model(model))

        return full_list

    for name, field_info in model.model_fields.items():
        field_type = field_info.annotation
        if field_type:
            if get_origin(field_type) is Union and type(None) in get_args(field_type):
                field_type = (
                    next((_type for _type in get_args(field_type) if _type is not type(None)), None) or field_type
                )

        _as_list = False
        if get_origin(field_type) is list:
            _as_list = True
            field_type = get_args(field_type)[0]

        _issubclass = False
        try:
            if field_type:
                _issubclass = issubclass(field_type, BaseModel)
        except TypeError:
            pass

        if field_type and _issubclass:
            result[name] = generate_example_model(field_type, as_list=_as_list)
        elif field_info.examples:
            result[name] = random.choice(field_info.examples)  # noqa: S311
        elif field_info.default:
            result[name] = field_info.default

        if isinstance(result[name], datetime):
            result[name] = result[name].isoformat()
        elif isinstance(result[name], Url):
            result[name] = str(result[name])

    return dict(result)
