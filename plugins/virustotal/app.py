"""Virustotal Clue Plugin

Maintaining Team/Organization: CCCS

Status: In Development

Clue Plugin to reach out to Virustotal and query for information about the given selectors.
"""

import base64
import os
import re
import sys
from typing import Any, Optional, Union
from urllib import parse as ul

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

VT_API_KEY = os.environ.get("VT_API_KEY", "")
MAX_TIMEOUT = float(os.environ.get("MAX_TIMEOUT", 3))
CLASSIFICATION = os.environ.get("CLASSIFICATION", "TLP:CLEAR")  # Classification of this service
API_URL = os.environ.get("API_URL", "https://www.virustotal.com/api/v3")  # override in case of mirror
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://www.virustotal.com/gui/search")  # override in case of mirror
PLUGIN_PORT = os.environ.get("PLUGIN_PORT", 8000)
EXECUTOR_THREADS = int(os.environ.get("EXECUTOR_THREADS", 32))

# verify can be boolean or path to CA file
verify: Union[str, bool] = str(os.environ.get("VT_VERIFY", "true")).lower()
if verify in ("true", "1"):
    verify = True
elif verify in ("false", "0"):
    verify = False
VERIFY = verify

if "pytest" not in sys.modules:
    # If we are not executing from inside a test, we will validate if the API key is present
    if not VT_API_KEY:
        logger.critical("VT_API_KEY environment variable is required.")
        exit(1)


# Mapping of Clue type names to VT types
TYPE_MAPPING: dict[str, str] = {
    "md5": "files",
    "sha1": "files",
    "sha256": "files",
    "domain": "domains",
    "ipv4": "ip_addresses",
    "ipv6": "ip_addresses",
    "url": "urls",
}


def lookup_type(type_name: str, value: str, timeout: float):
    """Lookup the type in VirusTotal.

    Values submitted must be URL encoded.

    Complete data from the lookup is returned unmodified.
    """
    if type_name == "files" and len(value) not in (32, 40, 64):
        raise UnprocessableException("Invalid hash provided. Require md5, sha1 or sha256")
    if not VT_API_KEY:
        raise UnprocessableException("No API Key is provided. An API Key is required.")

    session = requests.Session()
    headers = {
        "accept": "application/json",
        "x-apikey": VT_API_KEY,
    }
    # URLs must be converted into VT "URL identifiers"
    encoded_value = value
    if type_name == "urls":
        encoded_value = base64.urlsafe_b64encode(value.encode()).decode().strip("=")
    url = f"{API_URL}/{type_name}/{encoded_value}"

    try:
        rsp = session.get(url, headers=headers, verify=VERIFY, timeout=timeout)
    except requests.exceptions.Timeout as e:
        raise TimeoutException("VirusTotal failed to respond in time", cause=e)
    if rsp.status_code == 404:
        raise NotFoundException("No result found")
    elif rsp.status_code != 200:
        raise ClueException(f"Error submitting data to upstream [{rsp.status_code}]")

    return rsp.json().get("data", {})


def enrich(type_name: str, value: str, params: Params, token: Optional[str]):  # noqa: C901
    "Run virustotal enrichment on the specified value"
    tn = TYPE_MAPPING.get(type_name)
    if tn is None:
        raise InvalidDataException(f"{type_name} is not a valid type for this plugin.")
    data = lookup_type(type_name=tn, value=value, timeout=params.max_timeout)

    # Create result object
    search_encoded_value = ul.quote(ul.quote(value, safe=""), safe="")
    r = QueryEntry(
        classification=CLASSIFICATION,
        link=Url(f"{FRONTEND_URL}/{search_encoded_value}"),
        count=1,
        annotations=[],
        raw_data=data if params.raw else None,
    )

    if params.annotate:
        # Parse VT result attributes
        attrs = data.get("attributes", {})

        # IP address information block
        if type_name == "ipv4" and "as_owner" in attrs or type_name == "ipv6" and "as_owner" in attrs:
            summary = f"Owner: {attrs['as_owner']}"

            additional_details = []
            if "country" in attrs:
                additional_details.append(f"Country: {attrs['country']}")
            if "continent" in attrs:
                additional_details.append(f"Continent: {attrs['continent']}")

            summary += f"({', '.join(additional_details)})"
            details = attrs.get("whois", None)

            r.annotations.append(
                Annotation(
                    analytic="Virustotal - Owner information",
                    analytic_icon="simple-icons:virustotal",
                    type="context",
                    value=attrs["as_owner"],
                    summary=summary,
                    details=details,
                    icon=f"flag:{attrs['country'].lower()}-4x3" if "country" in attrs else None,
                    confidence=1,
                )
            )

        # Domain information block
        if type_name == "domain":
            whois = attrs.get("whois", "")

            try:
                owner = re.search(r"Admin Organization: (.*)", whois).group(1)  # type: ignore
            except AttributeError:
                owner = "N/A"

            try:
                country = re.search(r"Admin Country: (.*)", whois).group(1)  # type: ignore
            except AttributeError:
                country = "N/A"

            if owner.lower() not in ["n/a", "redacted for privacy"] or country.lower() not in [
                "n/a",
                "redacted for privacy",
            ]:
                summary = f"Owner: {owner} (Country: {country})"
                r.annotations.append(
                    Annotation(
                        analytic="Virustotal - Owner information",
                        analytic_icon="simple-icons:virustotal",
                        type="context",
                        value=owner,
                        summary=summary,
                        details=whois,
                        icon=(
                            f"flag:{country.lower()}-4x3"
                            if country.lower() not in ["n/a", "redacted for privacy"]
                            else None
                        ),
                        confidence=1,
                    )
                )

        # Malware Family attribution
        family_list = attrs.get("malware_config", {}).get("families", [])
        if family_list:
            families = " | ".join([f["family"] for f in family_list])
            r.annotations.append(
                Annotation(
                    analytic="Virustotal - Attribution",
                    analytic_icon="simple-icons:virustotal",
                    type="context",
                    value=families,
                    summary=f"{type_name.upper()} has been attributed to the following Malware Families: {families}",
                    confidence=1,
                )
            )

        # Look for scanners the found the files to be malicious or suspicious
        temp_annotations: dict[str, list[dict[str, Any]]] = {}
        for analysis_result in attrs["last_analysis_results"].values():
            verdict = analysis_result["category"]
            if verdict in ["malicious", "suspicious"]:
                temp_annotations.setdefault(verdict, [])
                temp_annotations[verdict].append(analysis_result)

        for verdict, engines in temp_annotations.items():
            engine_names = ", ".join([e["engine_name"] for e in engines])
            summary = f"{len(engines)} vendor found this {type_name.upper()} to be {verdict}: {engine_names}"
            details = []
            for e in engines:
                detail = f"### {e['engine_name']} results"
                for k in e.keys():
                    if k not in ["engine_name", "category", "method"]:
                        detail += f"\n{k}: {e[k]}"
                details.append(detail)

            r.annotations.append(
                Annotation(
                    analytic="Virustotal - Analysis",
                    analytic_icon="simple-icons:virustotal",
                    type="opinion",
                    value=verdict,
                    summary=summary,
                    details="\n\n".join(details),
                    confidence=1,
                    link=Url(f"{FRONTEND_URL}/{search_encoded_value}"),
                    quantity=len(engines),
                )
            )

        # Check if the requested type is safe
        stats = attrs["last_analysis_stats"]
        if stats["malicious"] == 0 and stats["suspicious"] == 0:
            r.annotations.append(
                Annotation(
                    analytic="Virustotal - Analysis",
                    analytic_icon="simple-icons:virustotal",
                    type="opinion",
                    value="benign",
                    summary=f"All of virustotal scanners found this {type_name.upper()} to be benign",
                    confidence=1,
                    link=Url(f"{FRONTEND_URL}/{search_encoded_value}"),
                )
            )

    return [QueryEntry.model_validate(r)]


plugin = CluePlugin(
    app_name=os.environ.get("APP_NAME", "virustotal"),
    classification=CLASSIFICATION,
    enable_apm=False,
    enable_cache=True,
    enrich=enrich,
    supported_types=set(TYPE_MAPPING.keys()),
    logger=logger,
)

app = plugin.app


def main():
    "Main executor function"
    plugin.app.run(host="0.0.0.0", port=int(os.environ.get("PLUGIN_PORT", os.environ.get("PORT", 8000))), debug=False)  # noqa: S104


if __name__ == "__main__":
    main()
