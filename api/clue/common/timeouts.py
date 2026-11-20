import math

from flask import request

from clue.common.exceptions import InvalidDataException


def parse_timeout(timeout: float = 5.0, *, maximum: float | None = None) -> float:
    """Parse and cap the request timeout in seconds using the configured limit."""
    if maximum is None:
        from clue.config import config

        maximum = config.api.maximum_timeout_request
    raw_timeout = request.args.get("max_timeout")
    try:
        timeout = float(raw_timeout) if raw_timeout is not None else timeout
    except ValueError as err:
        raise InvalidDataException("max_timeout must be a positive finite number.", status_code=400) from err
    if not math.isfinite(timeout) or timeout <= 0:
        raise InvalidDataException("max_timeout must be a positive finite number.", status_code=400)
    return min(timeout, maximum)
