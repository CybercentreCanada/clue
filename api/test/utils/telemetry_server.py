import json
import os
from datetime import datetime

import jwt
from flask import request

from clue.common.logging import get_logger
from clue.models.actions import Action, ActionResult, ExecuteRequest
from clue.models.network import QueryEntry
from clue.plugin import CluePlugin

logger = get_logger(__file__)


def enrich(type, value, params, token):
    data = json.loads(value)

    assert data["key1"] == "test"

    return QueryEntry(
        count=10,
        link="https://example.com",
        classification=os.environ.get("CLASSIFICATION", "TLP:CLEAR"),
        annotations=[
            {
                "type": "context",
                "value": "pride",
                "icon": "circle-flags:lgbt-progress",
                "confidence": 0.7,
                "summary": "This selector is an ally",
                "details": "# Breaking news\nThis selector is an ally",
                "analytic": "idk",
                "version": "0.0.3",
                "timestamp": datetime(2024, 1, 1, 1, 1, 1).isoformat(),
                "ubiquitous": True,
            },
        ],
        raw_data=[{"classification": os.environ.get("CLASSIFICATION", "TLP:CLEAR"), "data": '{"test": "raw data"}'}],
    )


def validate_token():
    header = request.headers.get("Authorization", None)
    if not header:
        return None, "Missing auth header"

    token = header.split(" ")[1]

    if "." not in token:
        return None, "Not a JWT"

    user = jwt.decode(jwt=token, options={"verify_aud": False, "verify_signature": False})

    if not user:
        return None, "No user parsed"

    return token, None


def run_action(action: Action, request: ExecuteRequest, token: str | None) -> ActionResult:
    if request.selector:
        return ActionResult(
            outcome="success",
            summary="We got a value",
            format="json",
            output={"value": json.loads(request.selector.value)["timestamp"]},
        )

    return ActionResult(
        outcome="success",
        summary="We got a value",
        format="json",
        output={"value": json.loads(request.selectors[0].value)["timestamp"]},
    )


plugin = CluePlugin(
    app_name="telemetry_server",
    supported_types={"telemetry"},
    enrich=enrich,
    classification=os.environ.get("CLASSIFICATION", "TLP:CLEAR"),
    logger=logger,
    enable_apm=False,
    enable_cache=False,
    validate_token=validate_token,
    actions=[
        Action[ExecuteRequest](
            id="retain",
            action_icon="codicon:terminal",
            name="Retention Action",
            classification="TLP:CLEAR",
            summary="Retain some stuff",
            supported_types={"telemetry"},
            accept_multiple=True,
        )
    ],
    run_action=run_action,
)

app = plugin.app

PORT = os.environ.get("PLUGIN_PORT", 10768)


def main():
    plugin.app.run(host="0.0.0.0", port=PORT, debug=False)


if __name__ == "__main__":
    main()
