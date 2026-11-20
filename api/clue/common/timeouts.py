import math

from flask import request

from clue.common.exceptions import InvalidDataException
from clue.config import config


def parse_timeout(timeout: float = 5.0, *, maximum: float | None = None) -> float:
    """Parse and cap the request timeout in seconds using the configured limit."""
    # Use the caller's limit when provided; otherwise use the central API limit.
    maximum = config.api.maximum_timeout_request if maximum is None else maximum
    user_timeout_request = request.args.get("max_timeout")

    try:
        timeout = float(user_timeout_request) if user_timeout_request is not None else timeout

    except ValueError as err:
        raise InvalidDataException("max_timeout must be a positive finite number.", status_code=400) from err

    if not math.isfinite(timeout) or timeout <= 0:
        raise InvalidDataException("max_timeout must be a positive finite number.", status_code=400)

    return min(timeout, maximum)
