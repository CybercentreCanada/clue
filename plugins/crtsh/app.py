"""This module was created by [Your Name].

Team: [Team Name]

Point of Contact: [Person Name] <user@email.com>

Status: In Development

[If not in use, provide a reason here, e.g., "The functionality has been replaced by a newer module,"
"The project it was part of has been deprecated," or "It is awaiting further development or review."]

[Optional: Add any additional context or notes about the module's purpose or history.]
"""

import datetime
import os
import textwrap
from typing import Any
from urllib.parse import urlsplit

import requests
from clue.common.exceptions import InvalidDataException, TimeoutException
from clue.common.logging import get_logger
from clue.models.network import Annotation, QueryEntry
from clue.plugin import CluePlugin
from clue.plugin.utils import Params
from pydantic import BaseModel, TypeAdapter

# Classification of this service
CLASSIFICATION = os.environ.get("CLASSIFICATION", "TLP:CLEAR")
# override in case of mirror
API_URL = os.environ.get("API_URL", "https://crt.sh/json")
# if historical certificates should be included - likely much slower/noisy, especially on major domains
INCLUDE_HISTORICAL = os.environ.get("INCLUDE_HISTORICAL", "false").lower() == "true"

logger = get_logger(__file__)

TYPES = {"domain", "url"}  # FUTURE: Could do IPs but this is super uncommon

plugin = CluePlugin(
    app_name=os.environ.get("APP_NAME", "crtsh"),
    classification=CLASSIFICATION,
    enable_apm=False,
    enable_cache=True,
    supported_types=TYPES,
    logger=logger,
)


class CrtSHCertificate(BaseModel):
    """Fragments of the TLS certificate found by crt.sh"""

    entry_timestamp: str | None = None
    issuer_name: str = ""
    name_value: str = ""
    not_before: str = ""
    not_after: str = ""
    serial_number: str = ""


CrtSHResponse = TypeAdapter(list[CrtSHCertificate])
"""Typical JSON response from crt.sh"""


def parse_entry_timestamp(value: str | None) -> datetime.datetime | None:
    """Parse the crt.sh entry timestamp when the upstream response includes one."""
    if not value:
        return None

    normalised_value = value.strip()
    if normalised_value.endswith("Z"):
        normalised_value = f"{normalised_value[:-1]}+00:00"

    try:
        return datetime.datetime.fromisoformat(normalised_value)
    except ValueError:
        pass

    for timestamp_format in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.datetime.strptime(normalised_value, timestamp_format)
        except ValueError:
            continue

    return None


@plugin.use
def enrich(type_name: str, value: str, params: Params, *_args) -> QueryEntry:
    "Enrich a given indicator"
    if type_name not in TYPES:
        raise InvalidDataException(message=f"Type name `{type_name}` is invalid. Valid types are: {', '.join(TYPES)}")

    # Normalize the query common name
    if type_name == "url":
        # We only want the domain component of this
        cn = urlsplit(value).netloc
    else:
        cn = value

    logger.info(f"Enriching [{type_name}] {cn} limit {params.limit} (annotate={params.annotate})")

    # Make a request to crt.sh on the common name field
    session = requests.Session()
    query_params: list[tuple[str, str]] = [("cn", cn), ("exclude", "expired")]

    try:
        # FUTURE: Determine if 1.0 is long enough for noisy domains (e.g. google)
        resp = session.get(API_URL, params=query_params, timeout=max(params.max_timeout - 0.5, 1.0))
    except requests.exceptions.Timeout as e:
        raise TimeoutException("crt.sh failed to respond in time.", cause=e)

    if resp.status_code != 200:
        raise InvalidDataException(f"Bad status from crt.sh: {resp.text}")

    data = CrtSHResponse.validate_json(resp.text)

    result = QueryEntry(classification=CLASSIFICATION, count=len(data))

    for cert in data[: params.limit]:
        normalised_name = cert.name_value.strip().replace("\n", ", ")
        annotation_args: dict[str, Any] = {
            "analytic": "crt.sh - TLS Certificate",
            "type": "context",
            "value": cert.serial_number,
            "summary": textwrap.dedent(f"""\
                TLS certificate found for domain:

                Common name(s) for certificate: {normalised_name}
                Not before: {cert.not_before}
                Not after: {cert.not_after}
                Certificate ID: {cert.serial_number}
                """),
            "confidence": 1,
        }

        if entry_timestamp := parse_entry_timestamp(cert.entry_timestamp):
            annotation_args["timestamp"] = entry_timestamp

        result.annotations.append(Annotation(**annotation_args))

    return result
