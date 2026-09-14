import hashlib
from datetime import datetime
from logging import Logger
from typing import Any
from urllib import parse as ul

from assemblyline_client import ClientError
from assemblyline_client.common.classification import Classification
from assemblyline_client.v4_client.client import Client
from clue.common.exceptions import InvalidDataException, NotFoundException
from clue.models.network import Annotation, QueryEntry
from clue.plugin.utils import Params
from consts import AL_URL_BASE, DEPLOYMENT_NAME, ENABLED_SOURCES, ICON, MAX_LIMIT
from pydantic_core import Url


class EnrichmentProcessor:
    """Processes and formats enrichment results from Assemblyline.

    This class provides methods to process and format results from Assemblyline
    searches, including results, alerts, safelist, and badlist. It handles
    classification, annotations, and links to the relevant Assemblyline pages.

    Attributes:
        c12n_engine: The classification engine used for determining classifications.
    """

    type_mappings = {
        "ipv4": "search_ip",
        "ipv6": "search_ip",
        "domain": "search_domain",
        "port": "search_port",
        "url": "search_uri",
        "email_address": "search_email",
        "md5": "search_md5",
        "sha1": "search_sha1",
        "sha256": "search_sha256",
    }

    def __init__(self, client: Client, c12n_engine: Classification, logger: Logger):
        self.client = client
        self.c12n_engine = c12n_engine
        self.logger = logger

    @staticmethod
    def supported_types():
        """Returns a list of supported types for enrichment.

        Returns:
            List of supported type names.
        """
        return list(EnrichmentProcessor.type_mappings.keys())

    def search_in_results(
        self,
        tag_type: str,
        value: str,
        limit: int = 25,
        annotate: bool = False,
        raw: bool = False,
    ):
        """Search for a tag in Assemblyline results.

        Args:
            self: EnrichmentProcessor instance
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
                    # Informative and above
                    f'result.sections.tags.network.static.{tag_type}:"{value}" OR '
                    f'result.sections.tags.network.dynamic.{tag_type}:"{value}" OR '
                    # Safelisted
                    f'result.sections.safelisted_tags.network.static.{tag_type}:"{value}" OR '
                    f'result.sections.safelisted_tags.network.dynamic.{tag_type}:"{value}"'
                )
                sha256 = None
                tag = (tag_type, value)
            else:
                query = f'result.sections.tags.network.{tag_type}:"{value}"'

        results = self.client.search.grouped.result(
            "response.service_name",
            group_sort="result.score desc",
            query=query,
            rows=min(limit, MAX_LIMIT),
            fl="*,id",
        )
        if results["items"]:
            return [self.results_for_result(results, query, annotate, raw=raw, sha256=sha256, tag=tag)]

        return []

    def search_in_alerts(
        self,
        tag_type: str,
        value: str,
        limit: int = 25,
        timeout: float = 3.0,
        annotate: bool = False,
        raw: bool = False,
    ):
        """Search for a tag in Assemblyline alerts.

        Args:
            client: Assemblyline client instance
            c12n_engine: Assemblyline classification engine
            tag_type: Type of tag to search for (e.g., 'ip', 'domain', 'sha256')
            value: Value to search for
            limit: Maximum number of results to return
            timeout: Maximum time to wait for results in seconds
            annotate: Whether to include annotation data
            raw: Whether to include raw result data

        Returns:
            List of QueryEntry objects with search results
        """
        if tag_type == "sha256":
            query = f"file.sha256:{value}"
            sha256 = value
            tag = None
        else:
            sha256 = None
            tag = (tag_type, value)
            query = f'al.{tag_type}:"{value}"'

        alerts = self.client.search.alert(query, rows=min(limit, MAX_LIMIT), timeout=int(timeout * 1000), fl="*,id")
        if alerts["items"]:
            return [self.results_for_alert(alerts, query, annotate, raw=raw, sha256=sha256, tag=tag)]

        return []

    def search_in_safebad_list(
        self,
        tag_type: str,
        value: str,
        annotate: bool = False,
        raw: bool = False,
        is_safe: bool = False,
    ):  # noqa: C901
        """Search for a tag in Assemblyline safelist or badlist.

        Args:
            client: Assemblyline client instance
            c12n_engine: Assemblyline classification engine
            tag_type: Type of tag to search for (e.g., 'ip', 'domain', 'sha256')
            value: Value to search for
            annotate: Whether to include annotation data
            raw: Whether to include raw result data
            is_safe: Whether to search safelist (True) or badlist (False)

        Returns:
            List of QueryEntry objects with search results
        """
        qhashes = []
        tag = (tag_type, value)

        if tag_type == "sha256":
            qhashes.append(value)
        elif tag_type in ["ip", "domain", "uri"]:
            for n_type in ["network.static", "network.dynamic"]:
                qhashes.append(hashlib.sha256(f"{n_type}.{tag_type}: {ul.unquote(value)}".encode("utf8")).hexdigest())
        elif tag_type == "email":
            qhashes.append(
                hashlib.sha256(f"network.{tag_type}.address: {ul.unquote(value)}".encode("utf8")).hexdigest()
            )
        elif tag_type == "port":
            qhashes.append(hashlib.sha256(f"network.{tag_type}: {ul.unquote(value)}".encode("utf8")).hexdigest())

        for qhash in qhashes:
            try:
                if is_safe:
                    item = self.client.safelist(qhash)
                else:
                    item = self.client.badlist(qhash)
                return [self.results_for_safebad_list(item, qhash, annotate, is_safe=is_safe, raw=raw, tag=tag)]

            except ClientError as e:
                if "The hash was not found" in str(e):
                    continue
                raise

        return []

    def search_ip(
        self,
        value: str,
        limit: int = 25,
        timeout: float = 3.0,
        annotate: bool = False,
        raw: bool = False,
    ):
        """Search for IP addresses in Assemblyline.

        Args:
            client: Assemblyline client instance
            c12n_engine: Assemblyline classification engine
            value: IP address to search for
            limit: Maximum number of results to return
            timeout: Maximum time to wait for results in seconds
            annotate: Whether to include annotation data
            raw: Whether to include raw result data

        Returns:
            List of QueryEntry objects with search results
        """
        return self.search_alertable_tag("ip", value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)

    def search_domain(
        self,
        value: str,
        limit: int = 25,
        timeout: float = 3.0,
        annotate: bool = False,
        raw: bool = False,
    ):
        """Search for domains in Assemblyline.

        Args:
            client: Assemblyline client instance
            c12n_engine: Assemblyline classification engine
            value: Domain to search for
            limit: Maximum number of results to return
            timeout: Maximum time to wait for results in seconds
            annotate: Whether to include annotation data
            raw: Whether to include raw result data

        Returns:
            List of QueryEntry objects with search results
        """
        return self.search_alertable_tag("domain", value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)

    def search_uri(
        self,
        value: str,
        limit: int = 25,
        timeout: float = 3.0,
        annotate: bool = False,
        raw: bool = False,
    ):
        """Search for URIs in Assemblyline.

        Args:
            client: Assemblyline client instance
            c12n_engine: Assemblyline classification engine
            value: URI to search for
            limit: Maximum number of results to return
            timeout: Maximum time to wait for results in seconds
            annotate: Whether to include annotation data
            raw: Whether to include raw result data

        Returns:
            List of QueryEntry objects with search results
        """
        return self.search_alertable_tag("uri", value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)

    def search_alertable_tag(
        self,
        tag_type: str,
        value: str,
        limit: int = 25,
        timeout: float = 3.0,
        annotate: bool = False,
        raw: bool = False,
    ):
        """Search for alertable tags across multiple Assemblyline sources.

        Searches alerts, results, safelist, and badlist based on enabled sources.

        Args:
            client: Assemblyline client instance
            c12n_engine: Assemblyline classification engine
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
                self.search_in_alerts(
                    tag_type=tag_type,
                    value=value,
                    limit=limit,
                    timeout=timeout,
                    annotate=annotate,
                    raw=raw,
                )
            )

        if "result" in ENABLED_SOURCES:
            response.extend(
                self.search_in_results(tag_type=tag_type, value=value, limit=limit, annotate=annotate, raw=raw)
            )

        if "safelist" in ENABLED_SOURCES:
            response.extend(
                self.search_in_safebad_list(tag_type=tag_type, value=value, annotate=annotate, raw=raw, is_safe=True)
            )

        if "badlist" in ENABLED_SOURCES:
            response.extend(
                self.search_in_safebad_list(tag_type=tag_type, value=value, annotate=annotate, raw=raw, is_safe=False)
            )

        if not response:
            raise NotFoundException(f"Tag {tag_type}:{value} not found in Assemblyline")

        return response

    def search_port(
        self,
        value: str,
        limit: int = 25,
        timeout: float = 3.0,
        annotate: bool = False,
        raw: bool = False,
    ):
        """Search for port numbers in Assemblyline.

        Args:
            client: Assemblyline client instance
            c12n_engine: Assemblyline classification engine
            value: Port number to search for
            limit: Maximum number of results to return
            timeout: Maximum time to wait for results in seconds
            annotate: Whether to include annotation data
            raw: Whether to include raw result data

        Returns:
            List of QueryEntry objects with search results
        """
        return self.search_tag("port", value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)

    def search_email(
        self,
        value: str,
        limit: int = 25,
        timeout: float = 3.0,
        annotate: bool = False,
        raw: bool = False,
    ):
        """Search for email addresses in Assemblyline.

        Args:
            client: Assemblyline client instance
            c12n_engine: Assemblyline classification engine
            value: Email address to search for
            limit: Maximum number of results to return
            timeout: Maximum time to wait for results in seconds
            annotate: Whether to include annotation data
            raw: Whether to include raw result data

        Returns:
            List of QueryEntry objects with search results
        """
        return self.search_tag("email", value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)

    def search_tag(
        self,
        tag_type: str,
        value: str,
        limit: int = 25,
        timeout: float = 3.0,
        annotate: bool = False,
        raw: bool = False,
    ):
        """Search for tags in Assemblyline results and safe/bad lists.

        Args:
            client: Assemblyline client instance
            c12n_engine: Assemblyline classification engine
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
            response.extend(
                self.search_in_results(tag_type=tag_type, value=value, limit=limit, annotate=annotate, raw=raw)
            )

        if "safelist" in ENABLED_SOURCES:
            response.extend(
                self.search_in_safebad_list(tag_type=tag_type, value=value, annotate=annotate, raw=raw, is_safe=True)
            )

        if "badlist" in ENABLED_SOURCES:
            response.extend(
                self.search_in_safebad_list(tag_type=tag_type, value=value, annotate=annotate, raw=raw, is_safe=False)
            )

        if not response:
            raise NotFoundException(f"Tag {tag_type}:{value} not found in Assemblyline")

        return response

    def search_sha1(
        self,
        value: str,
        limit: int = 25,
        timeout: float = 3.0,
        annotate: bool = False,
        raw: bool = False,
    ):
        """Search for SHA1 hashes in Assemblyline.

        Args:
            client: Assemblyline client instance
            c12n_engine: Assemblyline classification engine
            value: SHA1 hash to search for
            limit: Maximum number of results to return
            timeout: Maximum time to wait for results in seconds
            annotate: Whether to include annotation data
            raw: Whether to include raw result data

        Returns:
            List of QueryEntry objects with search results
        """
        return self.search_file("sha1", value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)

    def search_md5(
        self,
        value: str,
        limit: int = 25,
        timeout: float = 3.0,
        annotate: bool = False,
        raw: bool = False,
    ):
        """Search for MD5 hashes in Assemblyline.

        Args:
            client: Assemblyline client instance
            c12n_engine: Assemblyline classification engine
            value: MD5 hash to search for
            limit: Maximum number of results to return
            timeout: Maximum time to wait for results in seconds
            annotate: Whether to include annotation data
            raw: Whether to include raw result data

        Returns:
            List of QueryEntry objects with search results
        """
        return self.search_file("md5", value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)

    def search_sha256(
        self,
        value: str,
        limit: int = 25,
        timeout: float = 3.0,
        annotate: bool = False,
        raw: bool = False,
    ):
        """Search for SHA256 hashes in Assemblyline.

        Args:
            client: Assemblyline client instance
            c12n_engine: Assemblyline classification engine
            value: SHA256 hash to search for
            limit: Maximum number of results to return
            timeout: Maximum time to wait for results in seconds
            annotate: Whether to include annotation data
            raw: Whether to include raw result data

        Returns:
            List of QueryEntry objects with search results
        """
        return self.search_alertable_tag("sha256", value, limit=limit, timeout=timeout, annotate=annotate, raw=raw)

    def search_file(
        self,
        hash: str,
        value: str,
        limit: int = 25,
        timeout: float = 3.0,
        annotate: bool = False,
        raw: bool = False,
    ):
        """Search for files by hash in Assemblyline.

        Searches for files using the specified hash type and then searches for
        the SHA256 of any matching files.

        Args:
            client: Assemblyline client instance
            c12n_engine: Assemblyline classification engine
            hash: Type of hash to search for ('md5', 'sha1', 'sha256')
            value: Hash value to search for
            limit: Maximum number of results to return
            timeout: Maximum time to wait for results in seconds
            annotate: Whether to include annotation data
            raw: Whether to include raw result data

        Returns:
            List of QueryEntry objects with search results
        """
        # TODO: Add safelist and badlist searches
        file_query = f"{hash}:{value}"
        files = self.client.search.file(file_query, rows=1, timeout=int(timeout * 1000))
        if files["items"]:
            return self.search_sha256(
                files["items"][0]["sha256"],
                limit=limit,
                timeout=timeout,
                annotate=annotate,
                raw=raw,
            )

        raise NotFoundException(f"Hash {value} not found in Assemblyline")

    def results_for_safebad_list(self, data, qhash, annotate, is_safe, raw, tag):
        """Process and format results from Assemblyline safelist or badlist searches.

        Args:
            c12n_engine: Assemblyline classification engine
            data: Raw data from the safelist/badlist search
            qhash: Query hash used for the search
            annotate: Whether annotation data was requested
            is_safe: Whether this is a safelist (True) or badlist (False) result
            raw: Whether raw data was requested
            tag: Tag information (type, value) tuple

        Returns:
            QueryEntry object with formatted results and annotations
        """
        classification = self.c12n_engine.UNRESTRICTED
        annotations: list[Annotation] = []
        verdict_sources = []
        verdict = "benign" if is_safe else "malicious"
        source = "safelist" if is_safe else "badlist"
        if annotate:
            for item in data["sources"]:
                # Get the max classification
                classification = self.c12n_engine.max_classification(classification, item["classification"])

                verdict_sources.append(f"{item['name']} ({item['type']})")

        if verdict_sources:
            count = len(verdict_sources)

            if tag:
                summary = (
                    f"{DEPLOYMENT_NAME}'s {source} flagged this {tag[0].upper()} as {verdict} in {count} source(s): "
                )
            else:
                summary = f"{DEPLOYMENT_NAME}'s {source}  flagged this file as {verdict} in {count} sources(s): "
            summary = summary + ", ".join(verdict_sources)

            timestamp_str = data.get("updated", data.get("added"))
            timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else None

            annotations.append(
                Annotation(
                    analytic=f"{DEPLOYMENT_NAME} - {source.capitalize()}",
                    analytic_icon=ICON,
                    type="opinion",
                    value=verdict,
                    quantity=count,
                    summary=summary,
                    confidence=1,
                    link=Url(f"{AL_URL_BASE}/manage/{'safelist' if is_safe else 'badlist'}/{qhash}"),
                    timestamp=timestamp,  # type: ignore
                )
            )

        raw_data = data if raw else None

        self.logger.debug("%s opinion annotations returned", len(annotations))
        return QueryEntry(
            count=1,
            annotations=annotations,
            classification=classification,
            link=Url(f"{AL_URL_BASE}/manage/{'safelist' if is_safe else 'badlist'}/{qhash}"),
            raw_data=raw_data,
        )

    def results_for_alert(self, data, alert_query, annotate, sha256=None, raw=False, tag=None):  # noqa: C901
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
        classification = self.c12n_engine.UNRESTRICTED
        opinion_given = False
        annotations: list[Annotation] = []
        verdicts: dict[str, list[str]] = {"malicious": [], "suspicious": [], "benign": []}
        for item in data["items"]:
            # Get the max classification
            classification = self.c12n_engine.max_classification(classification, item["classification"])

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
                    verdicts[verdict].append(item["id"])

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
                        verdicts[verdict].append(item["id"])

        for verdict, ids in verdicts.items():
            count = len(ids)
            if not count:
                continue

            if tag:
                summary = (
                    f"{DEPLOYMENT_NAME} flagged this {tag[0].upper()} as {verdict} "
                    f"in {count} alerts due to its verdict value in the alert detail"
                )
                query = f"id:({' OR '.join(ids)})"
            else:
                summary = f"{DEPLOYMENT_NAME} flagged this file as {verdict} in {count} alert(s)"
                query = alert_query

            annotations.append(
                Annotation(
                    analytic=f"{DEPLOYMENT_NAME} - Alerts",
                    analytic_icon=ICON,
                    type="opinion",
                    value=verdict,
                    quantity=count,
                    summary=summary,
                    confidence=1,
                    link=Url(f"{AL_URL_BASE}/alerts?tc=&q={ul.quote(query)}"),
                )  # type: ignore
            )

        raw_data = data["items"] if raw else None

        self.logger.debug("%s total alert results, %s annotations returned", data["total"], len(annotations))
        return QueryEntry(
            count=data["total"],
            annotations=annotations,
            classification=classification,
            link=Url(f"{AL_URL_BASE}/alerts?tc=&q={ul.quote(alert_query)}"),
            raw_data=raw_data,
        )

    def _get_value(self, _dict: Any, value: str) -> Any:
        parts = value.split(".")
        for part in parts:
            _dict = _dict.get(part, None)
            if not _dict:
                break

        return _dict

    def results_for_result(self, data, result_query, annotate, sha256=None, raw=False, tag=None):  # noqa: C901
        """Process and format results from Assemblyline service result searches.

        Args:
            c12n_engine: Assemblyline classification engine
            data: Raw data from the service result search
            result_query: Query string used for the search
            annotate: Whether annotation data was requested
            sha256: SHA256 hash if searching by file hash
            raw: Whether raw data was requested
            tag: Tag information (type, value) tuple if searching by tag

        Returns:
            QueryEntry object with formatted results and annotations
        """
        classification = self.c12n_engine.UNRESTRICTED
        annotations: list[Annotation] = []
        verdicts: dict[str, set[str]] = {"malicious": set(), "suspicious": set(), "benign": set()}
        query_link = None
        verdict_to_docs: dict[str, list[str]] = {"malicious": [], "suspicious": [], "benign": []}
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
                        section_score = heuristic.get("score", 0)
                        network_tags = section["tags"].get("network") or {}
                        safe_tags = section["safelisted_tags"]
                        static_network_tags = network_tags.get("static") or {}
                        dynamic_network_tags = network_tags.get("dynamic") or {}
                        safe_static_network_tags = safe_tags.get(f"network.static.{tag_type}", [])
                        safe_dynamic_network_tags = safe_tags.get(f"network.dynamic.{tag_type}", [])
                        tag_values = (
                            self._get_value(network_tags, tag_type)
                            or self._get_value(static_network_tags, tag_type)
                            or self._get_value(dynamic_network_tags, tag_type)
                            or safe_static_network_tags
                            or safe_dynamic_network_tags
                            or []
                        )
                        if tag_value in tag_values:
                            verdict = None

                            if tag_value in safe_dynamic_network_tags + safe_static_network_tags:
                                # If the tag is safelisted by the system, we consider it benign regardless of the score
                                verdict = "benign"
                                analytic = "System Safelist"
                            elif section_score >= 1000:
                                verdict = "malicious"
                            elif section_score >= 300:
                                verdict = "suspicious"
                            elif section_score < 0:
                                verdict = "benign"

                            if verdict:
                                verdicts[verdict].add(analytic)
                                verdict_to_docs[verdict].append(item["id"])
                                break

                # Get the max classification
                self.logger.debug(
                    "Classification set to "
                    f"{self.c12n_engine.max_classification(classification, item['classification'])}, "
                    f"previously {classification}"
                )
                classification = self.c12n_engine.max_classification(classification, item["classification"])

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
                # Prepare query that targets the exact records that contributed to the verdict for more context.
                query = f"id:({' OR '.join(verdict_to_docs[verdict])})"
                query_link = Url(f"{AL_URL_BASE}/search/result?query={ul.quote(query)}")

                # Because the annotation link is what's displayable in the Clue UI, assign it the same value
                annotation_link = query_link

            annotations.append(
                Annotation(
                    analytic=f"{DEPLOYMENT_NAME} - Services",
                    analytic_icon=ICON,
                    type="opinion",
                    value=verdict,
                    quantity=len(services),
                    summary=summary,
                    confidence=1,
                    link=annotation_link,
                )  # type: ignore
            )

        raw_data = data["items"] if raw else None

        self.logger.debug("%s total opinion results, %s annotations returned", data["total"], len(annotations))
        return QueryEntry(
            count=data["total"],
            annotations=annotations,
            classification=classification,
            raw_data=raw_data,
            link=query_link,
        )

    def enrich(
        self,
        type_name: str,
        value: str,
        params: Params,
    ):
        """Lookup the type in Assemblyline.

        Values submitted must be URL encoded.

        Complete data from the lookup is returned unmodified.
        """
        if type_name not in self.type_mappings:
            raise InvalidDataException(f"Invalid type provided: {type_name}")

        return getattr(self, self.type_mappings[type_name])(
            value,
            limit=params.limit,
            timeout=params.max_timeout,
            annotate=params.annotate,
            raw=params.raw,
        )
