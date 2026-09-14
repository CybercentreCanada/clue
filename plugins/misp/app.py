"""MISP

Team: Monjiapawne

Status: In Development

MISP plugin enriches attributes, pulling data from attributes and their parent event.
Analysts can also report sightings back to MISP.
"""

import os
from datetime import datetime, timezone
from typing import Any, cast

from actions import ReportSighting, report_sighting
from client import misp_request
from clue.common.exceptions import ClueException, InvalidDataException, NotFoundException
from clue.common.logging import get_logger
from clue.models.actions import Action, ActionResult, ExecuteRequest
from clue.models.network import Annotation, QueryEntry
from clue.plugin import CluePlugin
from clue.plugin.utils import Params
from consts import (
    ACTIONS_ENABLED,
    ALLOW_TAGS,
    CLASSIFICATION,
    EXCLUDE_DECAYED,
    MISP_URL,
    THREAT_LEVEL,
    TLP_ENUM,
    TYPE_MAPPING,
)
from pydantic_core import Url

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


def _lookup_type(type_name: list[str], value: str, limit: int, timeout: float) -> list[dict[str, Any]]:
    """Lookup the type in MISP"""
    payload = {
        "type": type_name,
        "value": value,
        "limit": limit,
        "includeEventTags": True,
        "includeSightings": True,
        "excludeDecayed": EXCLUDE_DECAYED,
        "returnFormat": "json",
    }

    data = misp_request("post", "/attributes/restSearch", timeout, json=payload)
    if not isinstance(data, dict):
        raise ClueException(f"Unexpected response from MISP: {type(data).__name__}")

    attributes = data.get("response", {}).get("Attribute") or []
    if not attributes:
        raise NotFoundException("No result found")

    return attributes


def _highest_tlp(tag_names: list[str]) -> str | None:
    """Calculates the highest TLP from a list of unfiltered tags"""
    highest: str | None = None
    for tag in tag_names:
        tlp = TLP_ENUM.get(tag.upper())
        if tlp is not None:
            if highest is None or tlp > TLP_ENUM[highest]:
                highest = tag.upper()
    return highest


def _parse_misp_tag(tag_name: str) -> tuple[str, str, str]:
    """Parse MISP tag format"""
    # MISP tag structure <namespace:predicate="value">
    # https://www.misp-standard.org/rfc/misp-standard-taxonomy-format.html
    ns_pred, _, val = tag_name.partition("=")
    ns, _, pred = ns_pred.partition(":")
    # Values may be wrapped in single or double quotes and padded with whitespace
    val = val.strip(" \"'")

    return ns, pred, val


def _process_tags(attr_tags: list[dict[str, Any]]) -> tuple[set[str], set[str]]:
    """Extract display tags and canonical labels from attribute tags"""
    tags = set()
    labels = set()
    for tag in attr_tags:
        ns, pred, val = _parse_misp_tag(tag.get("name", ""))
        if not ns:
            ns = pred
            pred = ""

        if ns in ALLOW_TAGS or f"{ns}:{pred}" in ALLOW_TAGS:
            # Predicate may be empty for namespace only tags (e.g ecsirt="malware")
            key = pred or ns
            tag_output = f"{key}:{val}" if val else key
            tags.add(tag_output)

        # Canonical enrichment tags
        if f"{ns}:{pred}" == "misp-galaxy:threat-actor" and val:
            labels.add(val)
        if ns == "type":
            labels.add(pred)

    return tags, labels


@plugin.use
def enrich(type_name: str, value: str, params: Params, *_args) -> list[QueryEntry]:
    """Run MISP enrichment on the specified value"""
    tn = TYPE_MAPPING.get(type_name)
    if tn is None:
        raise InvalidDataException(f"{type_name} is not a valid type for this plugin.")
    data = _lookup_type(type_name=tn, value=value, limit=params.limit, timeout=params.max_timeout)

    logger.info(f"Enriching [{type_name}] {value} limit {params.limit} (annotate={params.annotate})")

    entries = []
    for attr in data:
        logger.debug(f"Processing attribute event_id={attr.get('event_id')}")

        # Event fields
        event = attr.get("Event", {})

        # Classification
        # Calculate both the attribute's and event's highest TLP and prefer the attributes
        attr_tlp = _highest_tlp([tag.get("name", "") for tag in attr.get("Tag", [])])
        event_tlp = _highest_tlp([tag.get("name", "") for tag in event.get("Tag", [])])
        attr_classification = attr_tlp or event_tlp or CLASSIFICATION

        annotations = []
        if params.annotate:
            # Attribute fields
            # Find best value with fallbacks, avoid irrelevant data
            attr_comment = attr.get("comment", "")
            if attr_comment == "Imported via the Freetext Import Tool":
                attr_comment = ""
            category = attr.get("category", "Unknown")

            sightings = attr.get("Sighting") or []
            true_sightings = sum(1 for s in sightings if s.get("type") == "0")  # 0 = true
            # Cap MISP confidence to 0.9, even with all true sightings MISP IOCs are still not absolute facts
            confidence = min(0.9, true_sightings / len(sightings)) if sightings else 0.5

            # Tags - only trust attribute tags to avoid misrepresentation (no fallback to event)
            tags, labels = _process_tags(attr.get("Tag", []))

            annotation_value = attr_comment or ", ".join(sorted(labels)) or "reported"

            # Attribute date range if we have both first and last
            first_seen_iso = attr.get("first_seen")
            last_seen_iso = attr.get("last_seen")
            active_range = None
            if first_seen_iso and last_seen_iso:
                first_seen = datetime.fromisoformat(first_seen_iso.replace("Z", "+00:00")).strftime("%Y-%m-%d")
                last_seen = datetime.fromisoformat(last_seen_iso.replace("Z", "+00:00")).strftime("%Y-%m-%d")
                active_range = f"Active: {first_seen} - {last_seen}"

            detail_parts = []
            if tags:
                detail_parts.append(f"**Tags**: {', '.join(sorted(tags))}")
            if active_range:
                detail_parts.append(active_range)
            details = "\n\n".join(detail_parts) or None

            # Timestamp
            # Last seen preferred, fallback to attribute modification time
            if last_seen_iso:
                timestamp = datetime.fromisoformat(last_seen_iso.replace("Z", "+00:00"))
            elif attr_ts := attr.get("timestamp"):
                timestamp = datetime.fromtimestamp(int(attr_ts or 0), tz=timezone.utc)
            else:
                continue  # attribute timestamp is guaranteed by MISP, guard against bad data

            org = event.get("Orgc", {}).get("name", "Unknown")
            event_title = event.get("info", "Unknown")
            summary = f"{org} reported {category}: {event_title}"

            annotations = [
                Annotation(
                    analytic="MISP",
                    analytic_icon="flowbite:messages-outline",
                    type="context",
                    link=Url(f"{MISP_URL}/events/view/{attr.get('event_id', '')}"),
                    value=annotation_value,
                    summary=summary,
                    details=details,
                    timestamp=timestamp,
                    confidence=confidence,
                    severity=THREAT_LEVEL.get(int(event.get("threat_level_id") or 0)),
                    quantity=true_sightings,
                )
            ]

        entries.append(
            QueryEntry(
                classification=attr_classification,
                count=1,
                annotations=annotations,
                raw_data=attr if params.raw else None,
            )
        )

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
