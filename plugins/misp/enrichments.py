from datetime import datetime, timezone
from typing import Any

from client import misp_request
from clue.common.exceptions import ClueException, NotFoundException
from clue.models.network import Annotation, QueryEntry
from clue.plugin.utils import Params
from consts import (
    ALLOW_TAGS,
    CLASSIFICATION,
    EXCLUDE_DECAYED,
    MISP_URL,
    THREAT_LEVEL,
    TLP_ENUM,
)
from pydantic_core import Url


def to_query_entry(attr: dict[str, Any], params: Params) -> QueryEntry:
    """Convert a single MISP attribute into a QueryEntry"""
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
        else:
            timestamp = datetime.fromtimestamp(int(attr["timestamp"]), tz=timezone.utc)

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

    return QueryEntry(
        classification=attr_classification,
        count=1,
        annotations=annotations,
        raw_data=attr if params.raw else None,
    )


def lookup_attributes(misp_types: list[str], value: str, limit: int, timeout: float) -> list[dict[str, Any]]:
    """Search MISP attributes by value

    Raises:
        NotFoundException: no attribute matched
        ClueException: MISP returned an unexpected response
    """
    payload = {
        "type": misp_types,
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
