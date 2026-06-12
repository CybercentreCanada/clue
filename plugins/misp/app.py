"""Misp

Team: Monjiapawne

Point of Contact: Monjia Pawne <iambrendamore@gmail.com>

Status: In Development

This plugin interfaces with MISP's API
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
API_URL = os.environ.get("API_URL", "")  # MISP is always self hosted

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
    "url": ["url"],
    "email_address": ["email-src", "email-dst"],
    "sha1": ["sha1"],
    "sha256": ["sha256"],
    "md5": ["md5"],
}

TLP_ENUM = {"TLP:CLEAR": 0, "TLP:GREEN": 1, "TLP:AMBER+STRICT": 2, "TLP:AMBER": 3, "TLP:RED": 4}


def lookup_type(type_name: list[str], value: str, timeout: float):
    if not MISP_API_KEY:
        raise UnprocessableException("No API key is provided. An API key is required")

    session = requests.Session()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": MISP_API_KEY,
    }
    payload = {
        "type": type_name,
        "value": value,
        "returnFormat": "json",
        "includeEventTags": True,
        "includeSightings": True,
    }

    url = f"{API_URL}/attributes/restSearch"
    logger.debug(f"URL {url}, Payload {payload}")

    try:
        rsp = session.post(url, json=payload, headers=headers, verify=VERIFY, timeout=timeout)
    except requests.exceptions.Timeout as e:
        raise TimeoutException("MISP failed to respond in time", cause=e)
    if rsp.status_code == 403:
        raise AuthenticationException(f"Authentication to MISP server: {API_URL} failed")
    elif not int(rsp.headers.get("X-Result-Count", 0)):
        raise NotFoundException("No result found")
    elif rsp.status_code != 200:
        raise ClueException(f"Error requesting data [{rsp.status_code}]")

    return rsp.json().get("response", {}).get("Attribute")


def _highest_tlp(tag_names: list[str]) -> str | None:
    """Calculate the highest TLP from a list of unfiltered tags"""
    highest: str | None = None
    for tag in tag_names:
        tlp = TLP_ENUM.get(tag.upper())
        if tlp is not None:
            if highest is None or tlp > TLP_ENUM[highest]:
                highest = tag.upper()
    return highest


def enrich(type_name: str, value: str, params: Params, token: str | None):
    tn = TYPE_MAPPING.get(type_name)
    if tn is None:
        raise InvalidDataException(f"{type_name} is not a valid type for this plugin.")
    data = lookup_type(type_name=tn, value=value, timeout=params.max_timeout)

    classification = CLASSIFICATION  # Give the attribute the highest TLP of the parent event(s)
    annotations = []
    if params.annotate:
        logger.info(f"Enriching [{type_name}] {value} limit {params.limit} (annotate={params.annotate})")

        for attr in data:
            # Prefer results from attributes but fallback to the parent event's data for fields that are not gareteed at the attribute level
            summary_parts = []
            event_id = attr.get("event_id", "")
            event = attr.get("Event", {})

            # Classification
            # Calculate both the attribute's and event's highest TLP and perfer the attributes
            attr_tlp = _highest_tlp([tag["name"] for tag in attr.get("Tag", [])])
            event_tlp = _highest_tlp([tag["name"] for tag in event.get("Tag", [])])
            attr_classification = attr_tlp or event_tlp or CLASSIFICATION
            if TLP_ENUM.get(attr_classification, 0) > TLP_ENUM.get(classification, 0):
                classification = attr_classification

            # Reporter
            summary_parts.append(f"Reported by {event.get('Orgc', {}).get('name')}")
            summary_parts.append(f"({attr.get("category")}):")

            # Atribute comment, fallback to event title
            attr_comment = attr.get("comment")
            event_title = event.get("info")
            summary_parts.append(attr_comment or event_title)

            # Sightings (true/false positives)
            sightings = attr.get("Sighting")
            true_sightings = 0
            false_sightings = 0
            if sightings:
                for sighting in sightings:
                    if sighting.get("type") == "1":
                        true_sightings += 1
                    else:
                        false_sightings += 1
                # TODO: Fix pluaral
                summary_parts.append(f"- {true_sightings} sightings, {false_sightings} false sightings")
            else:
                summary_parts.append("- no sightings reported")

            # Tags
            # TODO: Filter non tlp, non meta tags eg APT, Phishing

            summary = " ".join(summary_parts)

            annotations.append(
                Annotation(
                    analytic="MISP",
                    analytic_icon="tabler:message-dots",
                    type="context",
                    link=Url(f"{API_URL}/events/view/{event_id}"),
                    value=event_title,
                    summary=summary or event_title,
                    timestamp=datetime.fromtimestamp(int(attr["timestamp"]), tz=timezone.utc),
                    confidence=1.0,
                    quantity=true_sightings,
                )
            )

    r = QueryEntry(
        classification=classification,
        link=Url(f"{API_URL}"),
        count=len(data),
        annotations=annotations,
        raw_data=data if params.raw else None,
    )

    return [QueryEntry.model_validate(r)]


plugin = CluePlugin(
    app_name=os.environ.get("APP_NAME", "misp"),
    classification=CLASSIFICATION,
    enrich=enrich,
    supported_types=set(TYPE_MAPPING.keys()),
    logger=logger,
)
