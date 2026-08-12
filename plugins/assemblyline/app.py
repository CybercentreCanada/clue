"""Assemblyline Clue Plugin

Team: Canadian Centre for Cyber Security

Status: Production

This plugin enriches selectors based on their presence in Assemblyline alerts.
"""

import os
from typing import TYPE_CHECKING, cast

from clue.common.exceptions import ClueRuntimeError
from clue.common.logging import get_logger
from clue.models.actions import Action, ActionResult, ExecuteRequest
from clue.plugin import CluePlugin
from clue.plugin.utils import Params

from .actions import SubmitUrl, submit_url
from .auth import get_assemblyline_client
from .consts import ACTIONS_ENABLED, CLASSIFICATION
from .enrichments import EnrichmentProcessor

if TYPE_CHECKING:
    pass

TYPE_MAPPING = set(EnrichmentProcessor.supported_types())

logger = get_logger(__file__)


# MARK: Enrichment Endpoint
def enrich(type_name: str, value: str, params: Params, token: str | None):
    """Main enrichment function for the Assemblyline plugin.

    Routes enrichment requests to the appropriate search function based on the
    selector type.

    Args:
        type_name: Type of selector to enrich (e.g., 'ip', 'domain', 'sha256')
        value: Value to search for
        params: Enrichment parameters including limits and timeouts
        token: Authentication token from the central API

    Returns:
        List of QueryEntry objects with enrichment results

    Raises:
        NotFoundException: If no results are found for the selector
        InvalidDataException: If an invalid type is provided
    """
    with get_assemblyline_client() as (client, c12n_engine):
        proc = EnrichmentProcessor(client, c12n_engine, logger)
        return proc.enrich(type_name, value, params)


# MARK: Action Endpoint
def run_action(action: Action, request: ExecuteRequest, token: str | None) -> ActionResult:
    """Execute an action for the Assemblyline plugin.

    Currently supports the 'submit_url' action which submits URLs to
    Assemblyline for analysis.

    Args:
        action: The action definition containing action metadata
        request: The execution request containing selectors and parameters
        token: Authentication token from the central API

    Returns:
        ActionResult indicating success/failure and providing submission details
    """
    if action.id != "submit_url":
        return ActionResult(outcome="failure", summary=f"invalid action ID: {action.id}")

    request = cast(SubmitUrl, request)

    if request.selector is None or request.selector.type != "url":
        return ActionResult(outcome="failure", summary="submit_url action requires valid URL selector.")

    try:
        with get_assemblyline_client() as (client, c12n_engine):
            url, id = submit_url(client, c12n_engine, request)
    except ClueRuntimeError as e:
        return ActionResult(outcome="failure", summary=e.message)

    output = f"Submitted to Assemblyline, submission ID: {id}, internet connected: {request.internet_connected}"

    return ActionResult(
        outcome="success",
        summary="Submitted to Assemblyline",
        format="markdown",
        output=output,
        link=url,
    )


# MARK: Plugin Initialization
actions = []
if ACTIONS_ENABLED:
    actions = [
        Action[SubmitUrl](
            id="submit_url",
            action_icon="mdi:assembly",
            name="Submit to Assemblyline",
            classification=CLASSIFICATION,
            summary="Submits this URL to Assemblyline for further processing",
            supported_types={"url"},
            accept_multiple=False,
        )
    ]

plugin = CluePlugin(
    app_name=os.environ.get("APP_NAME", "assemblyline"),
    supported_types=TYPE_MAPPING,
    enrich=enrich,
    classification=CLASSIFICATION,
    logger=logger,
    actions=actions,
    run_action=run_action,
    enable_cache=False,
)
