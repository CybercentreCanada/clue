import math
import os
import time
from datetime import datetime, timezone

from flask import request
from pydantic import BaseModel

from clue.common.exceptions import InvalidDataException
from clue.common.logging import get_logger
from clue.common.timeouts import parse_timeout

# Default settings
MAX_LIMIT = int(os.environ.get("MAX_LIMIT", 100))
MAX_TIMEOUT = float(os.environ.get("MAX_TIMEOUT", 3))
MAX_REQUEST_TIMEOUT = float(os.environ.get("MAX_REQUEST_TIMEOUT", 60))
if not math.isfinite(MAX_REQUEST_TIMEOUT) or MAX_REQUEST_TIMEOUT <= 0:
    raise ValueError("MAX_REQUEST_TIMEOUT must be a positive finite number.")

logger = get_logger(__file__)


class Params(BaseModel):
    "A model build to parse arguments provided in the request object into a model"

    deadline: float
    "The epoch the central server wants to have a response by"

    max_timeout: float
    "The raw timeout value provided by the user"

    annotate: bool
    "Should the plugin return annotations about the given selector(s)?"

    raw: bool
    "Should the plugin return the raw data applicable to the given selector(s)?"

    limit: int
    "What is the maximum number of query entries that should be returned?"

    use_cache: bool
    "Does the request want to bypass any cached results?"

    @classmethod
    def from_request(cls):
        "Create a Params object from flask's request object"
        max_timeout = parse_timeout(MAX_TIMEOUT, maximum=MAX_REQUEST_TIMEOUT)
        now = time.time()
        raw_deadline = request.args.get("deadline")
        try:
            deadline = float(raw_deadline) if raw_deadline is not None else now + max_timeout
        except ValueError as err:
            raise InvalidDataException("deadline must be a finite number.", status_code=400) from err
        if not math.isfinite(deadline):
            raise InvalidDataException("deadline must be a finite number.", status_code=400)
        deadline = min(deadline, now + max_timeout)
        current_time = datetime.now(timezone.utc)
        if deadline > 0 and current_time.timestamp() > deadline:
            logger.warning(
                "Deadline %s was earlier than the current time, %s",
                str(datetime.fromtimestamp(deadline)),
                str(current_time),
            )

            raise RuntimeError("Deadline exceeded")

        logger.debug(
            "Deadline %s hits in %sms",
            str(datetime.fromtimestamp(deadline)),
            round((deadline - current_time.timestamp()) * 1000),
        )

        annotate = request.args.get("no_annotation", "false").lower() not in ("true", "1", "")
        use_cache = request.args.get("no_cache", "false").lower() not in ("true", "1", "")
        raw = request.args.get("include_raw", "false").lower() in ("true", "1", "")
        limit = request.args.get("limit", 100, type=int)
        if limit > int(MAX_LIMIT):
            limit = int(MAX_LIMIT)

        return cls(
            deadline=deadline, max_timeout=max_timeout, annotate=annotate, raw=raw, limit=limit, use_cache=use_cache
        )

    def __str__(self):
        # Make a string representation of the params that can be used for caching purposes
        # Deadline and max_timout are explicitely ignored otherwise it would never hit the cache
        return f"a={self.annotate},r={self.raw},l={self.limit}"
