import os
import time
from datetime import datetime, timezone

from flask import request
from pydantic import BaseModel

from clue.common.logging import get_logger

# Default settings
MAX_LIMIT = int(os.environ.get("MAX_LIMIT", 100))
MAX_TIMEOUT = float(os.environ.get("MAX_TIMEOUT", 3))

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
        max_timeout = request.args.get("max_timeout", MAX_TIMEOUT)
        try:
            max_timeout = float(max_timeout)
        except (ValueError, TypeError):
            max_timeout = MAX_TIMEOUT

        deadline = request.args.get("deadline", time.time() + max_timeout, type=float)
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
