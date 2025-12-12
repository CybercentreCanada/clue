import json
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import jwt
from flask import request
from pydantic import Field
from pydantic_core import Url

from clue.common.logging import get_logger
from clue.models.actions import Action, ActionResult, ExecuteRequest
from clue.models.fetchers import FetcherDefinition, FetcherResult
from clue.models.network import Annotation, QueryEntry
from clue.models.results.graph import GraphResult
from clue.models.results.image import ImageResult
from clue.models.results.status import StatusLabel, StatusResult
from clue.models.selector import Selector
from clue.plugin import CluePlugin

logger = get_logger(__file__)

with open(Path(__file__).parent.parent / "graphs" / "process.json", "r") as json_file:
    PROCESS_TREE = json.load(json_file)


def enrich(*args):
    return QueryEntry(
        count=10,
        link=Url("https://example.com"),
        classification=os.environ.get("CLASSIFICATION", "TLP:CLEAR"),
        annotations=[
            Annotation(
                type="opinion",
                value="malicious",
                confidence=0.7,
                severity=1.0,
                summary="This is a bad ip",
                details="# Breaking news\nThis is a bad IP",
                analytic="test enrichment",
                version="0.0.1",
                timestamp=datetime(2024, 1, 1, 1, 1, 1),
            ),
            Annotation(
                type="opinion",
                value="malicious",
                confidence=0.7,
                severity=1.0,
                summary="This is a bad ip",
                details="# Breaking news\nThis is a bad IP",
                author="this is author",
                version="0.0.1",
                timestamp=datetime(2024, 1, 1, 1, 1, 1),
            ),
            Annotation(
                type="context",
                value="pride",
                icon="circle-flags:lgbt-progress",
                confidence=0.7,
                summary="This selector is an ally",
                details="# Breaking news\nThis selector is an ally",
                analytic="idk",
                version="0.0.3",
                timestamp=datetime(2024, 1, 1, 1, 1, 1),
                ubiquitous=True,
            ),
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


class ChoiceEnum(str, Enum):
    a = "a"
    b = "b"
    c = "c"


class Params(ExecuteRequest):
    other_value: Optional[str] = Field(description="Another field you should show", default="")
    choice: ChoiceEnum = Field(default=ChoiceEnum.a, description="Another choice for you")
    other_choice: ChoiceEnum = Field(description="Another choice for you with no default")


def run_action(action: Action, request: ExecuteRequest, token: str | None) -> ActionResult:
    if action.id == "test_pivot":
        query = "potato"
        if request.selectors:
            query = "+or+".join(selector.value for selector in request.selectors)

        return ActionResult(
            outcome="success",
            summary="Opening google with your selector",
            format="pivot",
            output=Url(f"https://www.google.com/search?q={query}"),
        )
    if action.id == "test_context":
        if request.context is not None:
            # Demonstrate accessing typed fields
            context_info = {
                "context": request.context,
                "url": request.context.get("url"),
                "timestamp": request.context.get("timestamp"),
                "language": request.context.get("language"),
            }
            return ActionResult(
                outcome="success",
                summary="Context received",
                format="json",
                output=context_info,
            )
        else:
            return ActionResult(
                outcome="failure",
                summary="No context provided",
                format="json",
                output={"context": None},
            )

    if action.accept_empty:
        if request.selector:
            return ActionResult(
                outcome="failure",
                summary="We got a value",
                format="json",
                output={"value": request.selector.model_dump(mode="json", exclude_none=True)},
            )
        else:
            return ActionResult(
                outcome="success", summary="We don't got a value", format="json", output={"value": None}
            )

    if not isinstance(request, Params):
        return ActionResult(
            outcome="failure", summary="Invalid action request type", format="json", output={"value": None}
        )

    if request.choice == "c":
        return ActionResult(outcome="failure", summary="We don't got a value", format="json", output={"value": None})

    if request.other_value:
        return ActionResult(
            outcome="success", summary="We got a param value", format="json", output={"value": request.other_value}
        )

    if request.selector:
        return ActionResult(
            outcome="success",
            summary="We got a value",
            format="json",
            output={"value": request.selector.model_dump(mode="json", exclude_none=True)},
        )

    if request.selectors and action.accept_multiple:
        return ActionResult(
            outcome="success",
            summary="We got values",
            format="json",
            output={"values": [val.value for val in request.selectors]},
        )

    return ActionResult(outcome="failure", summary="We don't got a value", format="json", output={"value": None})


def setup_actions(*args, **kwargs):
    return [
        Action[ExecuteRequest](
            id="test_pivot",
            action_icon="mdi:link-box-variant-outline",
            name="Test Pivot",
            classification="TLP:CLEAR",
            summary="Execute a pivot",
            supported_types={"ip", "port", "sha256"},
            accept_multiple=True,
        ),
        Action[ExecuteRequest](
            id="test_context",
            action_icon="codicon:info",
            name="Test Context",
            classification="TLP:CLEAR",
            summary="Test context field",
            supported_types={"ip", "port", "sha256"},
            accept_multiple=False,
        ),
        Action[Params](
            id="test_action",
            action_icon="codicon:terminal",
            name="Test Action",
            classification="TLP:CLEAR",
            summary="Tester",
            supported_types={"ip", "port", "sha256"},
            accept_multiple=True,
        ),
        Action[Params](
            id="test_action_single",
            action_icon="codicon:terminal",
            name="Test Action",
            classification="TLP:CLEAR",
            summary="Tester",
            supported_types={"ip", "port", "sha256"},
            accept_multiple=False,
        ),
        Action[Params](
            id="test_action_empty",
            action_icon="codicon:terminal",
            name="Test Action",
            classification="TLP:CLEAR",
            summary="Tester",
            supported_types={"ip", "port", "sha256"},
            accept_multiple=False,
            accept_empty=True,
        ),
    ]


def run_fetcher(fetcher: FetcherDefinition, selector: Selector, access_token: str | None) -> FetcherResult:
    if fetcher.id == "json":
        return FetcherResult(outcome="success", format="json", data={"potato": "test"})

    if fetcher.id == "graph":
        return FetcherResult(outcome="success", format="graph", data=GraphResult.model_validate(PROCESS_TREE))

    if fetcher.id == "status":
        return FetcherResult(
            outcome="success",
            format="status",
            data=StatusResult(
                labels=[
                    StatusLabel(language="en", label="Status Label"),
                    StatusLabel(language="fr", label="La Status Label"),
                ],
                color="#f542f2",
            ),
        )

    return FetcherResult(
        outcome="success", format="image", data=ImageResult(image="https://example.com", alt="Alt Text")
    )


plugin = CluePlugin(
    app_name="test_server",
    supported_types={"ipv4", "ipv6", "port", "sha256"},
    logger=logger,
    enrich=enrich,
    classification=os.environ.get("CLASSIFICATION", "TLP:CLEAR"),
    enable_apm=False,
    enable_cache=True,
    validate_token=validate_token,
    setup_actions=setup_actions,
    run_action=run_action,
    fetchers=[
        FetcherDefinition(
            id="json",
            classification=os.environ.get("CLASSIFICATION", "TLP:CLEAR"),
            description="test fetcher json",
            format="json",
            supported_types={"ipv4", "ipv6", "port", "sha256"},
        ),
        FetcherDefinition(
            id="image",
            classification=os.environ.get("CLASSIFICATION", "TLP:CLEAR"),
            description="test fetcher image",
            format="image",
            supported_types={"ipv4", "ipv6", "port", "sha256"},
        ),
        FetcherDefinition(
            id="graph",
            classification=os.environ.get("CLASSIFICATION", "TLP:CLEAR"),
            description="test fetcher graph",
            format="graph",
            supported_types={"ipv4", "ipv6", "port", "sha256"},
        ),
        FetcherDefinition(
            id="status",
            classification=os.environ.get("CLASSIFICATION", "TLP:CLEAR"),
            description="test fetcher graph",
            format="status",
            supported_types={"ipv4", "ipv6", "port", "sha256"},
        ),
    ],
    run_fetcher=run_fetcher,
)

app = plugin.app

PORT = int(os.environ.get("PLUGIN_PORT", 10768))


def main():
    plugin.app.run(host="0.0.0.0", port=PORT, debug=False)


if __name__ == "__main__":
    main()
