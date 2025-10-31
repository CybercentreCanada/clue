"""Assemblyline Clue Plugin

Team: Canadian Centre for Cyber Security

Status: Production

This plugin enriches selectors based on their presence in Assemblyline alerts.
"""

import hashlib
import os
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Callable, Union, cast
from urllib import parse as ul

import assemblyline_client
from assemblyline_client import ClientError, get_client
from clue.common.exceptions import ClueRuntimeError, InvalidDataException, NotFoundException
from clue.common.logging import get_logger
from clue.models.actions import Action, ActionResult, ExecuteRequest
from clue.models.network import Annotation, QueryEntry
from clue.plugin import CluePlugin
from clue.plugin.utils import Params
from flask import request
from pydantic import Field
from pydantic_core import Url

if TYPE_CHECKING:
    from assemblyline_client.common.classification import Classification


logger = get_logger(__file__)

AL_TOKEN_PROVIDER = os.environ.get("AL_TOKEN_PROVIDER", "")
AL_API_KEY = os.environ.get("AL_API_KEY", "")
AL_USER = os.environ.get("AL_USER", "")
MAX_LIMIT = int(os.environ.get("MAX_LIMIT", 100))
MAX_TIMEOUT = float(os.environ.get("MAX_TIMEOUT", 3))
CLASSIFICATION = os.environ.get("CLASSIFICATION", "TLP:CLEAR")
AL_URL_BASE = os.environ.get("AL_URL_BASE", "https://assemblyline-ui")
PLUGIN_PORT = os.environ.get("PLUGIN_PORT", 8000)
ENABLED_SOURCES = set(os.environ.get("ENABLED_SOURCES", "result|alert|safelist|badlist").split("|"))
DEPLOYMENT_NAME = os.environ.get("DEPLOYMENT_NAME", "Assemblyline")
ACTIONS_ENABLED = os.environ.get("ACTIONS_ENABLED", "true").lower().strip() == "true"

# verify can be boolean or path to CA file
verify: Union[str, bool] = str(os.environ.get("VERIFY", "true")).lower()
if verify in ("true", "1"):
    verify = True
elif verify in ("false", "0"):
    verify = False
VERIFY = verify
CLIENT: assemblyline_client.Client4 | None = None
C12N_ENGINE: "Classification" = cast("Classification", None)


def initialize_with_retry(
    base_delay: float = 1.0, max_retries: int = 10
) -> assemblyline_client.Client3 | assemblyline_client.Client4:
    """Initialize the Assemblyline client with retry, exponential backoff, and a maximum retry count."""
    attempt = 0
    client: assemblyline_client.Client3 | assemblyline_client.Client4 | None = None
    while client is None and attempt < max_retries:
        try:
            client = get_client(AL_URL_BASE, apikey=(AL_USER, AL_API_KEY), verify=VERIFY, timeout=15)
        except Exception:
            logger.exception(f"Failed to initialize Assemblyline client (attempt {attempt + 1}):")
            delay = base_delay * (2**attempt)

            if delay > 60.0:
                delay = 60.0

            logger.info(f"Retrying in {delay:.1f} seconds...")

            time.sleep(delay)
            attempt += 1

    return client


@contextmanager
def inject_al_token():
    """Context manager to inject Assemblyline token for on-behalf-of (OBO) authentication.

    Sets up OBO token authentication for the CLIENT if AL_TOKEN_PROVIDER is configured
    and a Bearer token is present in the request headers. The token is cleared when
    exiting the context.
    """
    if AL_TOKEN_PROVIDER and CLIENT:
        token = request.headers.get("authorization", None)
        if token:
            bearer, token = token.split(" ")
            if bearer.lower() == "bearer":
                if "." in token:
                    CLIENT.set_obo_token(token, provider=AL_TOKEN_PROVIDER)

    try:
        yield None
    finally:
        if CLIENT:
            CLIENT.clear_obo_token()


def search_in_results(tag_type: str, value: str, limit: int = 25, annotate: bool = False, raw: bool = False):
    """Search for a tag in Assemblyline results.

    Args:
        tag_type: Type of tag to search for (e.g., 'ip', 'domain', 'sha256')
        value: Value to search for
        limit: Maximum number of results to return
        annotate: Whether to include annotation data
        raw: Whether to include raw result data

    Returns:
        List of QueryEntry objects with search results
    """
    if tag_type == "sha256":
        query = f"sha256:{value}"
        sha256 = value
        tag = None
    else:
        sha256 = None
        tag = (tag_type, value)

        if tag_type in ["ip", "domain", "uri"]:
            query = (
                f'result.sections.tags.network.static.{tag_type}:"{value}" OR '
                f'result.sections.tags.network.dynamic.{tag_type}:"{value}"'
            )
            sha256 = None
            tag = (tag_type, value)
        else:
            query = f'result.sections.tags.network.{tag_type}:"{value}"'

    if not CLIENT:
        logger.warning("Client is not set!")
        return []

    results = CLIENT.search.grouped.result(
        "response.service_name",
        group_sort="result.score desc",
        query=query,
        rows=min(limit, MAX_LIMIT),
        fl="*",
    )
    if results["items"]:
        return [results_for_result(results, query, annotate, raw=raw, sha256=sha256, tag=tag)]

    return []


def search_in_alerts(
    tag_type: str, value: str, limit: int = 25, timeout: float = 3.0, annotate: bool = False, raw: bool = False
):
    """Search for a tag in Assemblyline alerts.

    Args:
        tag_type: Type of tag to search for (e.g., 'ip', 'domain', 'sha256')
        value: Value to search for
        limit: Maximum number of results to return
        timeout: Maximum time to wait for results in seconds
        annotate: Whether to include annotation data
        raw: Whether to include raw result data

    Returns:
        List of QueryEntry objects with search results
    """
    if not CLIENT:
        logger.warning("Client is not set!")
        return []

    if tag_type == "sha256":
        query = f"file.sha256:{value}"
        sha256 = value
        tag = None
    else:
        sha256 = None
        tag = (tag_type, value)
        query = f'al.{tag_type}:"{value}"'

    alerts = CLIENT.search.alert(query, rows=min(limit, MAX_LIMIT), timeout=int(timeout * 1000), fl="*")
    if alerts["items"]:
        return [results_for_alert(alerts, query, annotate, raw=raw, sha256=sha256, tag=tag)]

    return []


def search_in_safebad_list(tag_type: str, value: str, annotate: bool = False, raw: bool = False, is_safe: bool = False):  # noqa: C901
    """Search for a tag in Assemblyline safelist or badlist.

    Args:
        tag_type: Type of tag to search for (e.g., 'ip', 'domain', 'sha256')
        value: Value to search for
        annotate: Whether to include annotation data
        raw: Whether to include raw result data
        is_safe: Whether to search safelist (True) or badlist (False)

    Returns:
        List of QueryEntry objects with search results
    """
    if not CLIENT:
        logger.warning("Client is not set!")
        return []

    qhashes = []
    tag = (tag_type, value)

    if tag_type == "sha256":
        qhashes.append(value)
    elif tag_type in ["ip", "domain", "uri"]:
        for n_type in ["network.static", "network.dynamic"]:
            qhashes.append(hashlib.sha256(f"{n_type}.{tag_type}: {ul.unquote(value)}".encode("utf8")).hexdigest())
    elif tag_type == "email":
        qhashes.append(hashlib.sha256(f"network.{tag_type}.address: {ul.unquote(value)}".encode("utf8")).hexdigest())
    elif tag_type == "port":
        qhashes.append(hashlib.sha256(f"network.{tag_type}: {ul.unquote(value)}".encode("utf8")).hexdigest())

    for qhash in qhashes:
        try:
            if is_safe:
                item = CLIENT.safelist(qhash)
            else:
                item = CLIENT.badlist(qhash)
            return [results_for_safebad_list(item, qhash, annotate, is_safe=is_safe, raw=raw, tag=tag)]

        except ClientError as e:
            if "The hash was not found" in str(e):
                continue
            raise

    return []


def search_ip(value: str, limit: int = 25, timeout: float = 3.0, annotate: bool = False, raw: bool = False):
    """Search for IP addresses in Assemblyline.

    Args:
        value: IP address to search for
        limit: Maximum number of results to return
        timeout: Maximum time to wait for results in seconds
        annotate: Whether to include annotation data
        raw: Whether to include raw result data

    Returns:
        List of QueryEntry objects with search results
    """
    return search_alertable_tag("ip", value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)


def search_domain(value: str, limit: int = 25, timeout: float = 3.0, annotate: bool = False, raw: bool = False):
    """Search for domains in Assemblyline.

    Args:
        value: Domain to search for
        limit: Maximum number of results to return
        timeout: Maximum time to wait for results in seconds
        annotate: Whether to include annotation data
        raw: Whether to include raw result data

    Returns:
        List of QueryEntry objects with search results
    """
    return search_alertable_tag("domain", value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)


def search_uri(value: str, limit: int = 25, timeout: float = 3.0, annotate: bool = False, raw: bool = False):
    """Search for URIs in Assemblyline.

    Args:
        value: URI to search for
        limit: Maximum number of results to return
        timeout: Maximum time to wait for results in seconds
        annotate: Whether to include annotation data
        raw: Whether to include raw result data

    Returns:
        List of QueryEntry objects with search results
    """
    return search_alertable_tag("uri", value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)


def search_alertable_tag(
    tag_type: str, value: str, limit: int = 25, timeout: float = 3.0, annotate: bool = False, raw: bool = False
):
    """Search for alertable tags across multiple Assemblyline sources.

    Searches alerts, results, safelist, and badlist based on enabled sources.

    Args:
        tag_type: Type of tag to search for (e.g., 'ip', 'domain', 'sha256')
        value: Value to search for
        limit: Maximum number of results to return
        timeout: Maximum time to wait for results in seconds
        annotate: Whether to include annotation data
        raw: Whether to include raw result data

    Returns:
        List of QueryEntry objects with search results from all enabled sources
    """
    response = []

    if "alert" in ENABLED_SOURCES:
        response.extend(
            search_in_alerts(tag_type=tag_type, value=value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)
        )

    if "result" in ENABLED_SOURCES:
        response.extend(search_in_results(tag_type=tag_type, value=value, limit=limit, annotate=annotate, raw=raw))

    if "safelist" in ENABLED_SOURCES:
        response.extend(
            search_in_safebad_list(tag_type=tag_type, value=value, annotate=annotate, raw=raw, is_safe=True)
        )

    if "badlist" in ENABLED_SOURCES:
        response.extend(
            search_in_safebad_list(tag_type=tag_type, value=value, annotate=annotate, raw=raw, is_safe=False)
        )

    return response


def search_port(value: str, limit: int = 25, timeout: float = 3.0, annotate: bool = False, raw: bool = False):
    """Search for port numbers in Assemblyline.

    Args:
        value: Port number to search for
        limit: Maximum number of results to return
        timeout: Maximum time to wait for results in seconds
        annotate: Whether to include annotation data
        raw: Whether to include raw result data

    Returns:
        List of QueryEntry objects with search results
    """
    return search_tag("network.port", value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)


def search_email(value: str, limit: int = 25, timeout: float = 3.0, annotate: bool = False, raw: bool = False):
    """Search for email addresses in Assemblyline.

    Args:
        value: Email address to search for
        limit: Maximum number of results to return
        timeout: Maximum time to wait for results in seconds
        annotate: Whether to include annotation data
        raw: Whether to include raw result data

    Returns:
        List of QueryEntry objects with search results
    """
    return search_tag("email.address", value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)


def search_tag(
    tag_type: str, value: str, limit: int = 25, timeout: float = 3.0, annotate: bool = False, raw: bool = False
):
    """Search for tags in Assemblyline results and safe/bad lists.

    Args:
        tag_type: Type of tag to search for
        value: Value to search for
        limit: Maximum number of results to return
        timeout: Maximum time to wait for results in seconds
        annotate: Whether to include annotation data
        raw: Whether to include raw result data

    Returns:
        List of QueryEntry objects with search results
    """
    response = []

    if "result" in ENABLED_SOURCES:
        response.extend(search_in_results(tag_type=tag_type, value=value, limit=limit, annotate=annotate, raw=raw))

    if "safelist" in ENABLED_SOURCES:
        response.extend(
            search_in_safebad_list(tag_type=tag_type, value=value, annotate=annotate, raw=raw, is_safe=True)
        )

    if "badlist" in ENABLED_SOURCES:
        response.extend(
            search_in_safebad_list(tag_type=tag_type, value=value, annotate=annotate, raw=raw, is_safe=False)
        )

    return []


def search_sha1(value: str, limit: int = 25, timeout: float = 3.0, annotate: bool = False, raw: bool = False):
    """Search for SHA1 hashes in Assemblyline.

    Args:
        value: SHA1 hash to search for
        limit: Maximum number of results to return
        timeout: Maximum time to wait for results in seconds
        annotate: Whether to include annotation data
        raw: Whether to include raw result data

    Returns:
        List of QueryEntry objects with search results
    """
    return search_file("sha1", value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)


def search_md5(value: str, limit: int = 25, timeout: float = 3.0, annotate: bool = False, raw: bool = False):
    """Search for MD5 hashes in Assemblyline.

    Args:
        value: MD5 hash to search for
        limit: Maximum number of results to return
        timeout: Maximum time to wait for results in seconds
        annotate: Whether to include annotation data
        raw: Whether to include raw result data

    Returns:
        List of QueryEntry objects with search results
    """
    return search_file("md5", value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)


def search_sha256(value: str, limit: int = 25, timeout: float = 3.0, annotate: bool = False, raw: bool = False):
    """Search for SHA256 hashes in Assemblyline.

    Args:
        value: SHA256 hash to search for
        limit: Maximum number of results to return
        timeout: Maximum time to wait for results in seconds
        annotate: Whether to include annotation data
        raw: Whether to include raw result data

    Returns:
        List of QueryEntry objects with search results
    """
    return search_alertable_tag("sha256", value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)


def search_file(
    hash: str, value: str, limit: int = 25, timeout: float = 3.0, annotate: bool = False, raw: bool = False
):
    """Search for files by hash in Assemblyline.

    Searches for files using the specified hash type and then searches for
    the SHA256 of any matching files.

    Args:
        hash: Type of hash to search for ('md5', 'sha1', 'sha256')
        value: Hash value to search for
        limit: Maximum number of results to return
        timeout: Maximum time to wait for results in seconds
        annotate: Whether to include annotation data
        raw: Whether to include raw result data

    Returns:
        List of QueryEntry objects with search results
    """
    if not CLIENT:
        logger.warning("Client is not set!")
        return []

    # TODO: Add safelist and badlist searches
    file_query = f"{hash}:{value}"
    files = CLIENT.search.file(file_query, rows=1, timeout=int(timeout * 1000))
    if files["items"]:
        return search_sha256(files["items"][0]["sha256"], limit=limit, timeout=timeout, annotate=annotate, raw=raw)

    return []


TYPE_MAPPING = {
    "ipv4": search_ip,
    "ipv6": search_ip,
    "domain": search_domain,
    "port": search_port,
    "url": search_uri,
    "email_address": search_email,
    "md5": search_md5,
    "sha1": search_sha1,
    "sha256": search_sha256,
}


def results_for_safebad_list(data, qhash, annotate, is_safe, raw, tag):
    """Process and format results from Assemblyline safelist or badlist searches.

    Args:
        data: Raw data from the safelist/badlist search
        qhash: Query hash used for the search
        annotate: Whether annotation data was requested
        is_safe: Whether this is a safelist (True) or badlist (False) result
        raw: Whether raw data was requested
        tag: Tag information (type, value) tuple

    Returns:
        QueryEntry object with formatted results and annotations
    """
    classification = C12N_ENGINE.UNRESTRICTED
    annotations: list[Annotation] = []
    verdict_sources = []
    verdict = "benign" if is_safe else "malicious"
    source = "safelist" if is_safe else "badlist"
    if annotate:
        for item in data["sources"]:
            # Get the max classification
            classification = C12N_ENGINE.max_classification(classification, item["classification"])

            verdict_sources.append(f"{item['name']} ({item['type']})")

    if verdict_sources:
        count = len(verdict_sources)

        if tag:
            summary = f"{DEPLOYMENT_NAME}'s {source} flagged this {tag[0].upper()} as {verdict} in {count} source(s): "
        else:
            summary = f"{DEPLOYMENT_NAME}'s {source}  flagged this file as {verdict} in {count} sources(s): "
        summary = summary + ", ".join(verdict_sources)

        annotations.append(
            Annotation(
                analytic=f"{DEPLOYMENT_NAME} - {source.capitalize()}",
                type="opinion",
                value=verdict,
                quantity=count,
                summary=summary,
                confidence=1,
                link=Url(f"{AL_URL_BASE}/manage/{'safelist' if is_safe else 'badlist'}/{qhash}"),
            )
        )

    raw_data = data["items"] if raw else None

    logger.debug("%s opinion annotations returned", len(annotations))
    return QueryEntry(
        count=1,
        annotations=annotations,
        classification=classification,
        link=Url(f"{AL_URL_BASE}/manage/{'safelist' if is_safe else 'badlist'}/{qhash}"),
        raw_data=raw_data,
    )


def results_for_alert(data, alert_query, annotate, sha256=None, raw=False, tag=None):  # noqa: C901
    """Process and format results from Assemblyline alert searches.

    Args:
        data: Raw data from the alert search
        alert_query: Query string used for the search
        annotate: Whether annotation data was requested
        sha256: SHA256 hash if searching by file hash
        raw: Whether raw data was requested
        tag: Tag information (type, value) tuple if searching by tag

    Returns:
        QueryEntry object with formatted results and annotations
    """
    classification = C12N_ENGINE.UNRESTRICTED
    opinion_given = False
    annotations: list[Annotation] = []
    verdicts = {"malicious": 0, "suspicious": 0, "benign": 0}
    for item in data["items"]:
        # Get the max classification
        classification = C12N_ENGINE.max_classification(classification, item["classification"])

        if opinion_given:
            continue

        if sha256 and annotate:
            alert_score = item["al"]["score"]
            verdict = None
            if alert_score >= 1000:
                verdict = "malicious"
            elif alert_score >= 300:
                verdict = "suspicious"
            elif alert_score < 0:
                verdict = "benign"
            if verdict:
                verdicts[verdict] += 1

        elif tag and annotate:
            tag_type, tag_value = tag
            for al_tag in item["al"]["detailed"][tag_type]:
                if al_tag["value"] != tag_value:
                    continue

                verdict = None
                if al_tag["verdict"] == "malicious":
                    verdict = "malicious"
                elif al_tag["verdict"] == "suspicious":
                    verdict = "suspicious"
                elif al_tag["verdict"] == "safe":
                    verdict = "benign"
                if verdict:
                    verdicts[verdict] += 1

    for verdict, count in verdicts.items():
        if not count:
            continue

        if tag:
            summary = (
                f"{DEPLOYMENT_NAME} flagged this {tag[0].upper()} as {verdict} "
                f"in {count} alerts due to its verdict value in the alert detail"
            )
        else:
            summary = f"{DEPLOYMENT_NAME} flagged this file as {verdict} in {count} alert(s)"

        annotations.append(
            Annotation(
                analytic=f"{DEPLOYMENT_NAME} - Alerts",
                type="opinion",
                value=verdict,
                quantity=count,
                summary=summary,
                confidence=1,
                link=Url(f"{AL_URL_BASE}/alerts?tc=&q={ul.quote(alert_query)}"),
            )
        )

    raw_data = data["items"] if raw else None

    logger.debug("%s total alert results, %s annotations returned", data["total"], len(annotations))
    return QueryEntry(
        count=data["total"],
        annotations=annotations,
        classification=classification,
        link=Url(f"{AL_URL_BASE}/alerts?tc=&q={ul.quote(alert_query)}"),
        raw_data=raw_data,
    )


def _get_value(_dict: Any, value: str) -> Any:
    parts = value.split(".")
    for part in parts:
        _dict = _dict.get(part, None)
        if not _dict:
            break

    return _dict


def results_for_result(data, result_query, annotate, sha256=None, raw=False, tag=None):  # noqa: C901
    """Process and format results from Assemblyline service result searches.

    Args:
        data: Raw data from the service result search
        result_query: Query string used for the search
        annotate: Whether annotation data was requested
        sha256: SHA256 hash if searching by file hash
        raw: Whether raw data was requested
        tag: Tag information (type, value) tuple if searching by tag

    Returns:
        QueryEntry object with formatted results and annotations
    """
    classification = C12N_ENGINE.UNRESTRICTED
    annotations: list[Annotation] = []
    verdicts: dict[str, set[str]] = {"malicious": set(), "suspicious": set(), "benign": set()}
    query_link = None
    for group in data["items"]:
        analytic = group["value"]
        for item in group["items"]:
            version = item["response"]["service_version"]
            tool_version = item["response"].get("service_tool_version")
            if tool_version:
                version += f" ({tool_version})"
            # if its a sha256 based results
            if sha256 and annotate:
                verdict = None
                if item["result"]["score"] >= 1000:
                    verdict = "malicious"
                elif item["result"]["score"] >= 300:
                    verdict = "suspicious"
                elif item["result"]["score"] < 0:
                    verdict = "benign"
                if verdict:
                    verdicts[verdict].add(analytic)
                    break
            elif tag and annotate:
                tag_type, tag_value = tag

                for section in item["result"]["sections"]:
                    heuristic = section.get("heuristic") or {}
                    if not heuristic:
                        continue

                    section_score = heuristic.get("score", 0)
                    if section_score == 0:
                        continue

                    network_tags = section["tags"].get("network") or {}
                    static_network_tags = network_tags.get("static") or {}
                    dynamic_network_tags = network_tags.get("dynamic") or {}
                    tag_values = (
                        _get_value(network_tags, tag_type)
                        or _get_value(static_network_tags, tag_type)
                        or _get_value(dynamic_network_tags, tag_type)
                        or []
                    )
                    if tag_value in tag_values:
                        verdict = None
                        if section_score >= 1000:
                            verdict = "malicious"
                        elif section_score >= 300:
                            verdict = "suspicious"
                        elif section_score < 0:
                            verdict = "benign"

                        if verdict:
                            verdicts[verdict].add(analytic)
                            break

            # Get the max classification
            logger.debug(
                f"Classification set to {C12N_ENGINE.max_classification(classification, item['classification'])}, "
                f"previously {classification}"
            )
            classification = C12N_ENGINE.max_classification(classification, item["classification"])

    verdict_query_map = {
        "malicious": "result.score:>=1000",
        "suspicious": "result.score:[300 TO 999]",
        "benign": "result.score:<300",
    }
    for verdict, services in verdicts.items():
        if not services:
            continue

        service_list = ", ".join(services)
        if tag:
            summary = (
                f"{len(services)} {DEPLOYMENT_NAME} service(s) flagged this "
                f"{tag[0].upper()} as {verdict}: {service_list}"
            )
        else:
            summary = f"{len(services)} {DEPLOYMENT_NAME} service(s) flagged this file as {verdict}: {service_list}"

        annotation_link = None
        if sha256:
            annotation_link = Url(f"{AL_URL_BASE}/file/detail/{sha256}")
        else:
            # Prepare query that targets verdicts
            query = f"({result_query}) AND {verdict_query_map[verdict]}"
            if services:
                # Add services to query to be more specific
                query += f" AND response.service_name:({' OR '.join(services)})"
            query_link = Url(f"{AL_URL_BASE}/search/result?query={ul.quote(query)}")

            # Because the annotation link is what's displayable in the Clue UI, assign it the same value
            annotation_link = query_link

        annotations.append(
            Annotation(
                analytic=f"{DEPLOYMENT_NAME} - Services",
                type="opinion",
                value=verdict,
                quantity=len(services),
                summary=summary,
                confidence=1,
                link=annotation_link,
            )
        )

    raw_data = data["items"] if raw else None

    logger.debug("%s total opinion results, %s annotations returned", data["total"], len(annotations))
    return QueryEntry(
        count=data["total"], annotations=annotations, classification=classification, raw_data=raw_data, link=query_link
    )


def lookup_type(
    func: Callable,
    value: str,
    limit: int = 25,
    timeout: float = 3.0,
    annotate: bool = False,
    raw: bool = False,
):
    """Lookup the type in Assemblyline.

    Values submitted must be URL encoded.

    Complete data from the lookup is returned unmodified.
    """
    with inject_al_token():
        resp = func(value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)

        if not resp:
            raise NotFoundException("No result found")

        return resp


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
    func = TYPE_MAPPING.get(type_name)
    if func is None:
        raise InvalidDataException("Invalid type provided")

    return lookup_type(
        func, value, limit=params.limit, timeout=params.max_timeout, annotate=params.annotate, raw=params.raw
    )


class SubmitUrl(ExecuteRequest):
    """Extended ExecuteRequest for URL submission actions.

    Adds an additional parameter to control whether internet-connected
    analysis should be enabled when submitting URLs to Assemblyline.

    Attributes:
        internet_connected: Whether to enable internet-connected analysis
    """

    internet_connected: bool = Field(description="If internet connected analysis should be enabled", default=False)


def submit_url(url: str, internet_connected: bool) -> tuple[Url, str]:
    """Submits a URL and returns a link to the submission."""
    if not CLIENT:
        logger.warning("Client is not set!")
        raise ClueRuntimeError("Client not initialized, submission was unsuccessful.")

    with inject_al_token():
        # Get the user's default submission parameters as this contains details services
        # to enable, alert parameters, TTL, etc
        submission_params = CLIENT.user.submission_params(CLIENT.current_user)

        # Mutate with local state
        submission_params["classification"] = CLASSIFICATION
        submission_params["description"] = "Forwarded from Clue"
        del submission_params["submitter"]  # This will be filled in by AL and is messy when proxying user creds

        if internet_connected:
            submission_params["services"]["selected"].append("Internet Connected")

        result = CLIENT.submit(url=url, params=submission_params)

    sid = result["sid"]
    report_url = Url(f"{AL_URL_BASE}/submission/detail/{sid}")
    return (report_url, sid)


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
        url, id = submit_url(request.selector.value, request.internet_connected)
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
    supported_types=set(TYPE_MAPPING.keys()),
    enrich=enrich,
    classification=CLASSIFICATION,
    logger=logger,
    actions=actions,
    run_action=run_action,
    enable_cache=False,
)

if "PYTEST_CURRENT_TEST" not in os.environ:
    # If we are not executing from inside a test, we will load the client
    if not AL_API_KEY or not AL_USER:
        print("AL_API_KEY and AL_USER are required environment variables.")  # noqa: T201
        exit(1)

    # Initialize AL client
    _client = initialize_with_retry()

    if isinstance(_client, assemblyline_client.Client3):
        # No OBO tokens in v3
        print("AL v3 not supported.")  # noqa: T201
        exit(1)

    CLIENT = _client
    C12N_ENGINE = _client.get_classification_engine()
