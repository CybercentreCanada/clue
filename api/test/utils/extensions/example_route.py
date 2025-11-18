from typing import Any

from clue.api import make_subapi_blueprint, ok
from clue.common.logging import get_logger

SUB_API = "test"
example_route = make_subapi_blueprint(SUB_API, api_version=1)
example_route._doc = "Test Endpoint"

logger = get_logger(__file__)


@example_route.route("/example", methods=["GET"])
def example_endpoint(**kwargs) -> tuple[dict[str, Any], int]:  # noqa C901
    "Test Endpoint"

    return ok()
