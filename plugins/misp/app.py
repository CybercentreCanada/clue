"""Misp

Team: Monjiapawne

Status: In Development

MISP plugin enriches attributes, pulling data from attributes and their parent event
"""

import os
from typing import Union
from datetime import datetime, timezone

import requests
from clue.common.exceptions import (
    ClueException,
    InvalidDataException,
    NotFoundException,
    UnprocessableException,
    TimeoutException,
    AuthenticationException,
)
from clue.common.logging import get_logger
from clue.models.network import Annotation, QueryEntry
from clue.plugin import CluePlugin
from clue.plugin.utils import Params
from pydantic_core import Url


logger = get_logger(__file__)

MISP_API_KEY = os.environ.get("MISP_API_KEY", "")
CLASSIFICATION = os.environ.get("CLASSIFICATION", "TLP:CLEAR")
API_URL = os.environ.get("API_URL", "https://misp.local")
EXCLUDE_DECAYED = str(os.environ.get("EXCLUDE_DECAYED", "true")).lower() in ("true", "1")

verify: Union[str, bool] = str(os.environ.get("MISP_VERIFY", "true")).lower()
if verify in ("true", "1"):
    verify = True
elif verify in ("false", "0"):
    verify = False
VERIFY = verify

TYPE_MAPPING: dict[str, list[str]] = {
    "ipv4": ["ip-src", "ip-dst"],
    "ipv6": ["ip-src", "ip-dst"],
    "mac_address": ["mac-address"],
    "domain": ["domain"],
    "url": ["url", "link"],
    "email_address": ["email-src", "email-dst"],
    "sha1": ["sha1"],
    "sha256": ["sha256"],
    "md5": ["md5"],
}

TLP_ENUM = {"TLP:CLEAR": 0, "TLP:GREEN": 1, "TLP:AMBER+STRICT": 2, "TLP:AMBER": 3, "TLP:RED": 4}

# Tags in MISP can be noisy, limit to known high impact tags
# filter tags by "namespace" or "namespace:predicate"
ALLOW_TAGS = {
    "ecsirt",
    "adversary",
    "malware_classification",
    "misp-galaxy:threat-actor",
    "misp-galaxy:malware",
    "misp-galaxy:tool",
    "misp-galaxy:ransomware",
    "misp-galaxy:sector",
}
# Allow users to append or override the default list
if extra := os.environ.get("ALLOW_TAGS_EXTRA"):
    ALLOW_TAGS = ALLOW_TAGS | {t.strip() for t in extra.split(",")}
if override := os.environ.get("ALLOW_TAGS"):
    ALLOW_TAGS = {t.strip() for t in override.split(",")}

# 4 (undefined), defaults to None
THREAT_LEVEL = {
    1: 0.75,  # High
    2: 0.5,  # Medium
    3: 0.25,  # Low
}

# Reuse TCP connections across requests, MISP returns 500 if too many connections
_session = requests.Session()

plugin = CluePlugin(
    app_name=os.environ.get("APP_NAME", "misp"),
    classification=CLASSIFICATION,
    enable_apm=False,
    enable_cache=True,
    supported_types=set(TYPE_MAPPING.keys()),
    logger=logger,
)


def lookup_type(type_name: list[str], value: str, limit: int, timeout: float):
    if not MISP_API_KEY:
        raise UnprocessableException("No API key is provided. An API key is required")

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": MISP_API_KEY,
    }
    payload = {
        "type": type_name,
        "value": value,
        "limit": limit,
        "includeEventTags": True,
        "includeSightings": True,
        "excludeDecayed": EXCLUDE_DECAYED,
        "returnFormat": "json",
    }
    url = f"{API_URL}/attributes/restSearch"

    try:
        rsp = _session.post(url, json=payload, headers=headers, verify=VERIFY, timeout=timeout)
    except requests.exceptions.Timeout as e:
        raise TimeoutException("MISP failed to respond in time", cause=e)
    except requests.exceptions.ConnectionError as e:
        raise ClueException(f"Failed to connect to MISP: {e}", cause=e)
    except requests.exceptions.RequestException as e:
        raise ClueException(f"Request failed: {e}", cause=e)

    if rsp.status_code == 403:
        raise AuthenticationException(f"Authentication to MISP server: {API_URL} failed")
    elif rsp.status_code != 200:
        raise ClueException(f"Error requesting data [{rsp.status_code}]")
    elif not int(rsp.headers.get("X-Result-Count", 0) or 0):
        raise NotFoundException("No result found")

    return rsp.json().get("response", {}).get("Attribute") or []


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
    val = val.strip('"')

    pred, _, _ = pred.partition(",")
    pred = pred.rstrip("'")

    return ns, pred, val


def _process_tags(attr_tags: list[dict]) -> tuple[set[str], set[str]]:
    """Extract display tags and canonical labels from attribute tags"""
    tags = set()
    labels = set()
    for tag in attr_tags:
        ns, pred, val = _parse_misp_tag(tag.get("name", ""))
        if not ns:
            ns = pred
            pred = ""

        if ns in ALLOW_TAGS or f"{ns}:{pred}" in ALLOW_TAGS:
            if val:
                tag_output = f"{pred}:{val}"
            else:
                tag_output = pred
            tags.add(tag_output)

        # Canonical enrichment tags
        if f"{ns}:{pred}" == "misp-galaxy:threat-actor" and val:
            labels.add(val)
        if ns == "type":
            labels.add(pred)

    return tags, labels


@plugin.use
def enrich(type_name: str, value: str, params: Params, *args):
    tn = TYPE_MAPPING.get(type_name)
    if tn is None:
        raise InvalidDataException(f"{type_name} is not a valid type for this plugin.")
    data = lookup_type(type_name=tn, value=value, limit=params.limit, timeout=params.max_timeout)

    logger.info(f"Enriching [{type_name}] {value} limit {params.limit} (annotate={params.annotate})")

    entries = []
    if params.annotate:
        for attr in data:
            logger.debug(f"Processing attribute event_id={attr.get('event_id')}")
            # Attribute fields
            # Find best value with fallbacks, avoid irrelevant data
            attr_comment = attr.get("comment", "")
            if attr_comment == "Imported via the Freetext Import Tool":
                attr_comment = ""
            category = attr.get("category")

            sightings = attr.get("Sighting") or []
            true_sightings = sum(1 for s in sightings if s.get("type") == "0")  # 0 = true
            if sightings:
                # Cap MISP confidence to 0.9, even with all true sightings MISP IOCs are still not absolute facts
                confidence = min(0.9, true_sightings / len(sightings))
            else:
                confidence = 0.5

            # Tags - only trust attribute tags to avoid misrepresentation (no fallback to event)
            tags, labels = _process_tags(attr.get("Tag", []))

            annotation_value = attr_comment or ", ".join(labels) or "reported"

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
                timestamp = datetime.fromtimestamp(int(attr_ts), tz=timezone.utc)
            else:
                continue

            # Event fields
            event = attr.get("Event", {})

            org = event.get("Orgc", {}).get("name", "Unknown")
            event_title = event.get("info")
            summary = f"{org} reported {category}: {event_title}"

            # Classification
            # Calculate both the attribute's and event's highest TLP and prefer the attributes
            attr_tlp = _highest_tlp([tag["name"] for tag in attr.get("Tag", [])])
            event_tlp = _highest_tlp([tag["name"] for tag in event.get("Tag", [])])
            attr_classification = attr_tlp or event_tlp or CLASSIFICATION

            entries.append(
                QueryEntry(
                    classification=attr_classification,
                    link=Url(f"{API_URL}"),
                    count=1,
                    annotations=[
                        Annotation(
                            analytic="MISP",
                            analytic_icon="flowbite:messages-outline",
                            type="context",
                            link=Url(f'{API_URL}/events/view/{attr.get("event_id", "")}'),
                            value=annotation_value,
                            summary=summary,
                            details=details,
                            timestamp=timestamp,
                            confidence=confidence,
                            severity=THREAT_LEVEL.get(int(event.get("threat_level_id", 0))),
                            quantity=true_sightings,
                        )
                    ],
                    raw_data=attr if params.raw else None,
                )
            )

    logger.info(f"Returning {len(entries)} entries for {type_name}={value}")

    return entries
