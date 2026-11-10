"""MISP

Team: Monjiapawne

Status: In Development

MISP plugin enriches attributes, pulling data from attributes and their parent event.
Analysts can also report sightings back to MISP.
"""

import os
from typing import cast

from actions import ReportSighting, report_sighting
from clue.common.exceptions import InvalidDataException, NotFoundException
from clue.common.logging import get_logger
from clue.models.actions import Action, ActionResult, ExecuteRequest
from clue.models.network import QueryEntry
from clue.plugin import CluePlugin
from clue.plugin.utils import Params
from consts import (
    ACTIONS_ENABLED,
    CLASSIFICATION,
    TYPE_MAPPING,
)
from enrichments import lookup_attributes, to_query_entry

logger = get_logger(__file__)

actions = []
if ACTIONS_ENABLED:
    actions = [
        Action[ReportSighting](
            id="report_sighting",
            action_icon="bi:eye",
            name="Report a sighting",
            summary="Reports this indicator, adding a sighting in MISP",
            classification=CLASSIFICATION,
            supported_types=set(TYPE_MAPPING.keys()),
            accept_multiple=True,
        )
    ]

plugin = CluePlugin(
    app_name=os.environ.get("APP_NAME", "misp"),
    classification=CLASSIFICATION,
    enable_apm=False,
    enable_cache=True,
    supported_types=set(TYPE_MAPPING.keys()),
    logger=logger,
    actions=actions,
)


@plugin.use
def enrich(type_name: str, value: str, params: Params, *_args) -> list[QueryEntry]:
    """Run MISP enrichment on the specified value"""
    misp_types = TYPE_MAPPING.get(type_name)
    if misp_types is None:
        raise InvalidDataException(f"{type_name} is not a valid type for this plugin.")

    logger.info(f"Enriching [{type_name}] {value} limit {params.limit} (annotate={params.annotate})")
    attributes = lookup_attributes(misp_types, value, limit=params.limit, timeout=params.max_timeout)

    entries = [to_query_entry(attr, params) for attr in attributes]
    logger.info(f"Returning {len(entries)} entries for {type_name}={value}")

    return entries


@plugin.use
def run_action(action: Action, request: ExecuteRequest, token: str | None) -> ActionResult:
    """Execute an action for the MISP plugin.

    Supports 'report_sighting' action which reports a sighting to
    MISP.

    Args:
        action: The action definition containing action metadata
        request: The execution request containing selectors and parameters
        token: Authentication token from the central API

    Returns:
        ActionResult indicating success/failure and providing submission details
    """
    if action.id != "report_sighting":
        return ActionResult(outcome="failure", summary=f"invalid action ID: {action.id}")

    sighting_request = cast(ReportSighting, request)

    values = [s.value for s in sighting_request.selectors]

    try:
        report_sighting(values, sighting_request)
    except NotFoundException:
        return ActionResult(outcome="failure", summary="MISP recorded no sightings, no attribute matched.")

    plural = "" if len(values) == 1 else "s"
    # Prevent markdown from rendering
    formatted = ", ".join(f"`{v.replace('`', '')}`" for v in values)
    output = f"Reported sighting{plural} for {formatted} as **{sighting_request.sighting_type}**."

    return ActionResult(
        outcome="success",
        summary=f"Reported sighting{plural} to MISP",
        format="markdown",
        output=output,
    )
