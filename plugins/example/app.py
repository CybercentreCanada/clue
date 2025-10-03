"""This module was created by CCCS.

Team: CCCS

Point of Contact: [Matthew Rafuse] <matthew.rafuse@cyber.gc.ca>

Status: In Development

[If not in use, provide a reason here, e.g., "The functionality has been replaced by a newer module,"
"The project it was part of has been deprecated," or "It is awaiting further development or review."]

[Optional: Add any additional context or notes about the module's purpose or history.]
"""

import json
import os
import textwrap
from pathlib import Path

from clue.common.exceptions import InvalidDataException
from clue.common.logging import get_logger
from clue.models.actions import Action, ActionResult, ExecuteRequest
from clue.models.fetchers import FetcherDefinition, FetcherResult
from clue.models.network import Annotation, QueryEntry
from clue.models.results.graph import GraphResult
from clue.models.results.image import ImageResult
from clue.models.results.status import StatusLabel, StatusResult
from clue.models.selector import Selector
from clue.plugin import CluePlugin
from clue.plugin.utils import Params
from pydantic_core import Url

CLASSIFICATION = os.environ.get("CLASSIFICATION", "TLP:CLEAR")

logger = get_logger(__file__)

with open(Path(__file__).parent / "process.json", "r") as json_file:
    PROCESS_TREE = json.load(json_file)

TYPES = {"ipv4", "ipv6", "domain", "url", "email_address", "telemetry"}


def enrich(type_name: str, value: str, params: Params, *_args) -> QueryEntry:
    "Enrich a given indicator"
    if type_name not in TYPES:
        raise InvalidDataException(
            message=f"Type name `{type_name}` is invalid. Valid types are: {', '.join(TYPES)}"
        )

    logger.info(
        f"Enriching [{type_name}] {value} limit {params.limit} (annotate={params.annotate})"
    )

    result = QueryEntry(
        classification=CLASSIFICATION,
        count=1,
        link=Url("https://example.com"),
        annotations=[
            Annotation(
                analytic="Test Plugin",
                analytic_icon="fluent-color:checkmark-circle-16",
                icon="fluent-color:checkmark-circle-16",
                type="context",
                value=value,
                link=Url("https://example.com"),
                details=textwrap.dedent(
                    f"""
                # Test Enrichment

                Type: {type_name}

                Value: {value}
                """
                ),
                summary=f"Test Enrichment - type: {type_name}, value: {value}",
                confidence=1.0,
            )
        ],
    )

    return result


def run_action(
    action: Action, request: ExecuteRequest, token: str | None
) -> ActionResult:
    "Execute a test action"
    logger.info("Recieved %s", repr(request))

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

    if action.id.endswith("single"):
        return ActionResult(
            outcome="success",
            summary="We got a single request",
            format="json",
            output=request.model_dump(mode="json"),
            link=Url("https://google.com"),
        )

    summary = textwrap.dedent(
        f"""
        # Single Selector Data

        Type: {request.selector.type if request.selector else "N/A"}
        Value: {request.selector.value if request.selector else "N/A"}
        Classification: {request.selector.classification if request.selector else "N/A"}

        # Multiple Selectors Data
        {str(request.selectors)}
        """
    ).strip()

    return ActionResult(
        outcome="success",
        summary="We got a request",
        format="markdown",
        output=summary,
        link=Url("https://example.com"),
    )


def run_fetcher(
    fetcher: FetcherDefinition, selector: Selector, access_token: str | None
) -> FetcherResult:
    if fetcher.id == "json":
        return FetcherResult(outcome="success", format="json", data={"potato": "test"})

    if fetcher.id == "graph":
        return FetcherResult(
            outcome="success",
            format="graph",
            data=GraphResult.model_validate(PROCESS_TREE),
        )

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
        outcome="success",
        format="image",
        data=ImageResult(
            image="https://upload.wikimedia.org/wikipedia/commons/thumb/4/40/Canada_goose_on_Seedskadee_NWR"
            "_%2827826185489%29.jpg/788px-Canada_goose_on_Seedskadee_NWR_%2827826185489%29.jpg",
            alt="Alt Text",
        ),
    )


plugin = CluePlugin(
    app_name=os.environ.get("APP_NAME", "test-plugin"),
    classification=CLASSIFICATION,
    enable_apm=False,
    enable_cache=True,
    enrich=enrich,
    supported_types=TYPES,
    logger=logger,
    actions=[
        Action[ExecuteRequest](
            id="test_action",
            action_icon="codicon:terminal",
            name="Test Action",
            classification="TLP:CLEAR",
            summary="Execute a test action",
            supported_types=TYPES,
            accept_multiple=True,
        ),
        Action[ExecuteRequest](
            id="test_action_single",
            action_icon="codicon:terminal",
            name="Test Action (Single)",
            classification="TLP:CLEAR",
            summary="Execute a test action (single)",
            supported_types=TYPES,
            accept_multiple=False,
        ),
        Action[ExecuteRequest](
            id="test_pivot",
            action_icon="mdi:link-box-variant-outline",
            name="Test Pivot",
            classification="TLP:CLEAR",
            summary="Execute a pivot",
            supported_types=TYPES,
            accept_multiple=True,
        ),
    ],
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


def main():
    """Main application function"""
    plugin.app.run(
        host="0.0.0.0",  # noqa: S104
        port=int(os.environ.get("PLUGIN_PORT", os.environ.get("PORT", 8000))),
        debug=bool(os.environ.get("DEBUG", "False").capitalize()),
    )


if __name__ == "__main__":
    main()
