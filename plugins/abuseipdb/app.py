"""AbuseIPDB Clue Plugin

Maintaining Team/Organization: CCCS

Status: In Development

Clue plugin to query AbuseIPDB reputation information for IP selectors.
"""

import os
from typing import Any, Union

import requests
from clue.common.exceptions import (
    ClueException,
    InvalidDataException,
    NotFoundException,
    TimeoutException,
    UnprocessableException,
)
from clue.common.logging import get_logger
from clue.models.network import Annotation, QueryEntry
from clue.plugin import CluePlugin
from clue.plugin.utils import Params
from pydantic_core import Url

logger = get_logger(__file__)

ABUSEIPDB_API_KEY = os.environ.get("ABUSEIPDB_API_KEY", os.environ.get("ABUSEIPDB_KEY", ""))
CLASSIFICATION = os.environ.get("CLASSIFICATION", "TLP:CLEAR")
API_URL = os.environ.get("ABUSEIPDB_API_URL", os.environ.get("API_URL", "https://api.abuseipdb.com/api/v2/check"))
FRONTEND_URL = os.environ.get(
    "ABUSEIPDB_FRONTEND_URL", os.environ.get("FRONTEND_URL", "https://www.abuseipdb.com/check")
)
MAX_AGE_IN_DAYS = int(os.environ.get("ABUSEIPDB_MAX_AGE_IN_DAYS", os.environ.get("MAX_AGE_IN_DAYS", "90")))
SUPPORTED_TYPES = {"ipv4", "ipv6"}

verify: Union[str, bool] = str(os.environ.get("ABUSEIPDB_VERIFY", "true"))
verify_bool = verify.lower()
if verify_bool in ("true", "1"):
    verify = True
elif verify_bool in ("false", "0"):
    verify = False
VERIFY = verify


def lookup_ip(value: str, params: Params) -> dict[str, Any]:
    """Lookup an IP address in AbuseIPDB."""
    if not ABUSEIPDB_API_KEY:
        raise UnprocessableException("No API key is provided. Set ABUSEIPDB_API_KEY or ABUSEIPDB_KEY.")

    headers = {
        "Accept": "application/json",
        "Key": ABUSEIPDB_API_KEY,
    }
    query_params = {
        "ipAddress": value,
        "maxAgeInDays": MAX_AGE_IN_DAYS,
        "verbose": "true",
    }

    try:
        response = requests.get(API_URL, headers=headers, params=query_params, verify=VERIFY, timeout=params.max_timeout)
    except requests.exceptions.Timeout as e:
        raise TimeoutException("AbuseIPDB failed to respond in time.", cause=e)

    if response.status_code == 404:
        raise NotFoundException("No result found")
    if response.status_code == 401:
        raise UnprocessableException("AbuseIPDB API key was rejected.")
    if response.status_code == 422:
        raise InvalidDataException("AbuseIPDB rejected the supplied IP address.")
    if response.status_code != 200:
        raise ClueException(f"Error submitting data to AbuseIPDB [{response.status_code}]")

    data = response.json().get("data", {})
    if not data:
        raise NotFoundException("No result found")
    return data


def enrich(type_name: str, value: str, params: Params, *_args) -> QueryEntry:
    """Run AbuseIPDB enrichment on an IP selector."""
    if type_name not in SUPPORTED_TYPES:
        raise InvalidDataException(
            message=f"Type name `{type_name}` is invalid. Valid types are: {', '.join(sorted(SUPPORTED_TYPES))}"
        )

    data = lookup_ip(value, params)
    abuse_confidence = int(data.get("abuseConfidenceScore") or 0)
    total_reports = int(data.get("totalReports") or 0)
    country_code = data.get("countryCode")
    domain = data.get("domain")
    isp = data.get("isp")
    usage_type = data.get("usageType")
    frontend_link = Url(f"{FRONTEND_URL}/{value}")

    result = QueryEntry(
        classification=CLASSIFICATION,
        link=frontend_link,
        count=1 if total_reports or abuse_confidence else 0,
        annotations=[],
        raw_data=data if params.raw else None,
    )

    if not params.annotate:
        return result

    summary_parts = [f"Abuse confidence score: {abuse_confidence}%", f"Reports: {total_reports}"]
    if country_code:
        summary_parts.append(f"Country: {country_code}")
    if domain:
        summary_parts.append(f"Domain: {domain}")
    if isp:
        summary_parts.append(f"ISP: {isp}")
    if usage_type:
        summary_parts.append(f"Usage: {usage_type}")

    verdict = "malicious" if abuse_confidence >= 75 else "suspicious" if abuse_confidence > 0 else "benign"
    annotation_type = "opinion" if verdict != "benign" else "context"

    result.annotations.append(
        Annotation(
            analytic="AbuseIPDB - IP Reputation",
            analytic_icon="simple-icons:abuseipdb",
            type=annotation_type,
            value=verdict,
            summary="; ".join(summary_parts),
            confidence=abuse_confidence / 100 if abuse_confidence else 1,
            quantity=total_reports,
            link=frontend_link,
            icon=f"flag:{country_code.lower()}-4x3" if country_code else None,
        )
    )

    return result


plugin = CluePlugin(
    app_name=os.environ.get("APP_NAME", "abuseipdb"),
    classification=CLASSIFICATION,
    enable_apm=False,
    enable_cache=True,
    enrich=enrich,
    supported_types=SUPPORTED_TYPES,
    logger=logger,
)

app = plugin.app


def main():
    """Main executor function."""
    plugin.app.run(host="0.0.0.0", port=int(os.environ.get("PLUGIN_PORT", os.environ.get("PORT", 8000))), debug=False)  # noqa: S104


if __name__ == "__main__":
    main()