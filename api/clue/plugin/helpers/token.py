import base64
import json
import re
from typing import Optional, cast

from flask import request

from clue.common.exceptions import InvalidDataException


def get_username(token: Optional[str] = None, claims: list[str] | None = None):
    "Get the username from a given token. Provide an optional list of claims to use"
    if not token:
        token = cast(str, request.headers.get("Authorization", None, type=str)).split()[1]

    if not token or "." not in token:
        raise InvalidDataException("Function requires a JWT to parse username")

    jwt = json.loads(base64.b64decode(token.split(".")[1] + "==").decode())

    if claims is None:
        claims = ["email", "upn", "unique_name", "preferred_username"]

    username = None
    for claim in claims:
        username = jwt.get(claim, None)

        if username:
            break

    if not username:
        username = re.sub(r"[^a-z]+", "_", jwt["name"].lower())

    return username
