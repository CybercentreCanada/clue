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
PLUGIN_PORT = os.environ.get("PLUGIN_PORT", 8000)

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


def lookup_type(type_name: list[str], value: str, timeout: float):
    if not MISP_API_KEY:
        raise UnprocessableException("No API key is provided. An API key is required")

    session =  requests.Session()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": MISP_API_KEY,
    }
    payload = {
        "type": type_name,
        "value": value,
        "returnFormat": "json"
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


def enrich(type_name: str, value: str, params: Params, token: str | None):
    tn = TYPE_MAPPING.get(type_name)
    if tn is None:
        raise InvalidDataException(f"{type_name} is not a valid type for this plugin.")
    data = lookup_type(type_name=tn, value=value, timeout=params.max_timeout)

    annotations = []
    if params.annotate:
        logger.info(f"Enriching [{type_name}] {value} limit {params.limit} (annotate={params.annotate})")

        for attr in data:
            additional_details = []

            # Root
            event_id = attr.get("event_id", "")

            # Event
            event = attr.get("Event", {})
            event_title = event.get("info", event_id)

            # Tag
            # TODO: Clean tag output, filter TLP
            tags = [tag["name"] for tag in attr.get("Tag", [])]
            if tags:
                additional_details.append("Tags: " + ", ".join(tags))


            annotations.append(Annotation(
                analytic="MISP - Events",                # tool/source for producing
                analytic_icon="tabler:message-dots",
                type="context",                          # type of result, misp is facts only
                link=Url(f"{API_URL}/events/view/{event_id}"),
                value=event_title,                         # event id or title in misp
                summary=", ".join(additional_details),     # full sentence "misp event : seen in phising targeting fin sector"
                timestamp=datetime.fromtimestamp(int(attr["timestamp"]), tz=timezone.utc),
                confidence=1.0,                          # misp fact only
            ))

    r = QueryEntry(
        classification=CLASSIFICATION,
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
