import math
import os
from hashlib import sha256
from urllib.parse import urljoin

import requests
from flask import request
from pydantic import TypeAdapter, ValidationError
from requests import JSONDecodeError
from requests.adapters import HTTPAdapter, Retry

from clue.common.logging import get_logger
from clue.models.actions import ActionResult, ActionSpec
from clue.models.fetchers import FetcherDefinition, FetcherResult
from clue.models.network import QueryEntry
from clue.models.selector import Selector
from clue.plugin.models import BulkEntry

CENTRAL_SERVER_URL = os.getenv("CENTRAL_API_URL", "http://enrichment-rest.enrichment.svc.cluster.local:5000")

logger = get_logger(__file__)

# Module-level session cache keyed by sha256(url:retries).
_SESSIONS: dict[str, requests.Session] = {}


def _get_session(base_url: str, retries: int) -> requests.Session:
    """Return a cached, retry-configured :class:`requests.Session` for *base_url*.

    Sessions are keyed by ``(base_url, retries)``. Request timeout is provided
    per call and does not affect Session or adapter configuration.
    """
    cache_key = sha256(f"{base_url}:{retries}".encode()).hexdigest()
    if cache_key not in _SESSIONS:
        session = requests.Session()
        pool_size = max(1, math.floor(int(os.environ.get("EXECUTOR_THREADS", 32)) / 2))
        retry_strategy = Retry(
            total=retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(
            pool_connections=pool_size,
            pool_maxsize=pool_size,
            max_retries=retry_strategy,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        _SESSIONS[cache_key] = session
    return _SESSIONS[cache_key]


def _connect_to_central_server(retries: int = 3) -> tuple[requests.Session, dict[str, str]]:
    """Return a ``(session, headers)`` pair for calling the central server.

    Token extraction priority:

    1. ``X-Clue-Authorization`` — a pre-OBO'd token forwarded by the central API.
       Used as the primary ``Authorization`` bearer. The original ``Authorization``
       token is included as ``X-Clue-Authorization`` so the central API can
       propagate it further downstream if needed.
    2. ``Authorization`` — the raw user bearer token, used when no pre-OBO token
       is present.

    The returned *session* is shared across calls (pooled); the returned *headers*
    dict is scoped to the current request and must not be mutated after use.
    """
    clue_token = request.headers.get("X-Clue-Authorization", None)
    raw_auth = request.headers.get("Authorization", None)
    auth_token = raw_auth.split(" ", 1)[1] if raw_auth and " " in raw_auth else None

    if clue_token:
        logger.info("X-Clue-Authorization header specified, using pre-OBO token")
        primary_token = clue_token
        secondary_token = auth_token  # forward original as X-Clue-Authorization
    elif auth_token:
        logger.warning("X-Clue-Authorization header not specified, falling back to Authorization header")
        primary_token = auth_token
        secondary_token = None
    else:
        logger.warning("No token specified, continuing with no authentication")
        primary_token = None
        secondary_token = None

    headers: dict[str, str] = {"Accept": "application/json", "Content-Type": "application/json"}
    if primary_token:
        headers["Authorization"] = f"Bearer {primary_token}"
    if secondary_token:
        headers["X-Clue-Authorization"] = secondary_token

    session = _get_session(CENTRAL_SERVER_URL, retries)
    return session, headers


def _safe_central_get(
    url: str,
    session: requests.Session,
    headers: dict[str, str],
    timeout: float = 5.0,
) -> dict | None:
    """Make a GET request to the central server with standardized error handling.

    Args:
        url: The full URL to request.
        session: A cached ``requests.Session`` from ``_get_session()``.
        headers: Request headers dict from ``_connect_to_central_server()``.
        timeout: HTTP timeout in seconds. Defaults to 5.0.

    Returns:
        The ``api_response`` dict from the response body on success, or ``None``
        on any connection, parse, or HTTP error.
    """
    try:
        rsp = session.get(url, headers=headers, timeout=timeout)
        rsp.raise_for_status()
        return rsp.json().get("api_response", {})
    except requests.exceptions.ConnectionError:
        logger.exception("Unable to connect to central server at %s", url)
    except requests.exceptions.Timeout:
        logger.exception("Timeout calling central server %s", url)
    except (JSONDecodeError, KeyError, AttributeError):
        logger.exception("Central server returned unexpected format for %s", url)
    except requests.exceptions.HTTPError:
        logger.exception("HTTP error from central server %s", url)
    return None


def _safe_central_post(
    url: str,
    session: requests.Session,
    headers: dict[str, str],
    json_body: dict | list | None = None,
    params: dict | None = None,
    timeout: float | tuple[float, float] = 5.0,
) -> dict | None:
    """Make a POST request to the central server with standardized error handling.

    Args:
        url: The full URL to request.
        session: A cached ``requests.Session`` from ``_get_session()``.
        headers: Request headers dict from ``_connect_to_central_server()``.
        json_body: JSON payload to POST, or ``None``.
        params: Query parameters dict, or ``None``.
        timeout: HTTP timeout in seconds or (connect, read) tuple. Defaults to 5.0.

    Returns:
        The ``api_response`` dict from the response body on success, or ``None``
        on any connection, parse, or HTTP error.
    """
    try:
        rsp = session.post(url, json=json_body, params=params, headers=headers, timeout=timeout)
        rsp.raise_for_status()
        return rsp.json().get("api_response", {})
    except requests.exceptions.ConnectionError:
        logger.exception("Unable to connect to central server at %s", url)
    except requests.exceptions.Timeout:
        logger.exception("Timeout calling central server %s", url)
    except (JSONDecodeError, KeyError, AttributeError):
        logger.exception("Central server returned unexpected format for %s", url)
    except requests.exceptions.HTTPError:
        logger.exception("HTTP error from central server %s", url)
    return None


def get_sources() -> dict[str, list[str]]:
    """Return the types supported by each plugin visible to the current user.

    Calls ``GET /api/v1/lookup/types/`` on the central server. Results are
    filtered server-side by the user's classification — no local filtering is
    performed here.

    Returns:
        A dict mapping each source name to its list of supported type names,
        e.g. ``{"geoip": ["ipv4", "ipv6"], "vt": ["ipv4", "domain", ...]}``.
        Returns an empty dict on any connection or parse error.
    """
    session, headers = _connect_to_central_server()
    url = urljoin(CENTRAL_SERVER_URL, "/api/v1/lookup/types/")
    result = _safe_central_get(url, session, headers)
    return result if result is not None else {}


def enrich(
    sources: str | list[str],
    selectors: Selector | list[Selector],
    *,
    limit: int = 10,
    timeout: float = 5.0,
    no_annotation: bool = False,
    include_raw: bool = False,
    no_cache: bool = False,
) -> dict[str, dict[str, dict[str, BulkEntry]]]:
    """Run bulk enrichment on one or more selectors via the central API.

    Plugins can call this helper to query other plugins before or during their
    own enrichment — for example, invoking a geolocation plugin on an IP address
    and using the result to produce a richer annotation.

    A single :class:`~clue.models.selector.Selector` or source string is
    automatically promoted to a list.

    Args:
        sources: Plugin name(s) to target. Pass an empty list to query all sources
            available to the current user.
        selectors: One or more :class:`~clue.models.selector.Selector` objects.
        limit: Maximum result items returned per source per selector. Defaults to 10.
        timeout: HTTP timeout in seconds. Defaults to 5.0.
        no_annotation: Omit annotation data from results. Defaults to ``False``.
        include_raw: Include raw plugin data in results. Defaults to ``False``.
        no_cache: Bypass the cache and re-query plugins directly. Defaults to ``False``.

    Returns:
        A three-level dict ``{type: {value: {source: BulkEntry}}}`` mirroring the
        structure returned by the central ``/api/v1/lookup/enrich`` endpoint.
        Returns an empty dict on connection or parse errors.
    """
    if isinstance(sources, str):
        sources = [sources]
    if isinstance(selectors, Selector):
        selectors = [selectors]

    session, headers = _connect_to_central_server()
    url = urljoin(CENTRAL_SERVER_URL, "/api/v1/lookup/enrich")

    params: dict[str, str | int | float | bool] = {
        "limit": limit,
        "max_timeout": max(timeout * 0.95, 0.5),
    }
    if sources:
        params["sources"] = "|".join(sources)
    if no_annotation:
        params["no_annotation"] = True
    if include_raw:
        params["include_raw"] = True
    if no_cache:
        params["no_cache"] = True

    payload = [s.model_dump(exclude_none=True, exclude_unset=True) for s in selectors]
    result: dict[str, dict[str, dict[str, BulkEntry]]] = {}

    api_response = _safe_central_post(
        url,
        session,
        headers,
        json_body=payload,
        params=params,
        timeout=(timeout, timeout * 3),
    )
    if api_response is None:
        return result

    _parse_enrich_response(api_response, result)
    return result


def _parse_enrich_response(
    api_response: dict,
    result: dict[str, dict[str, dict[str, BulkEntry]]],
) -> None:
    """Parse the central-API bulk-enrich response into the *result* dict in-place.

    Central response shape: ``{type: {value: {source: QueryResult}}}``.
    """
    for type_name, values in api_response.items():
        result.setdefault(type_name, {})
        for value, sources_data in values.items():
            result[type_name].setdefault(value, {})
            for source_name, query_result in sources_data.items():
                try:
                    items = [QueryEntry.model_validate(item) for item in (query_result.get("items") or [])]
                    result[type_name][value][source_name] = BulkEntry(
                        error=query_result.get("error"),
                        items=items,
                        raw_data=query_result.get("raw_data"),
                    )
                except Exception:
                    logger.exception("Failed to parse result from source %s for %s/%s", source_name, type_name, value)
                    result[type_name][value][source_name] = BulkEntry(
                        error=f"Failed to parse response from {source_name}"
                    )


def list_actions() -> dict[str, ActionSpec]:
    """List all actions available on the central server for the current user.

    Calls ``GET /api/v1/actions/`` and returns a dict keyed by
    ``"<plugin_id>.<action_id>"``, filtered server-side by user classification.

    Returns:
        A dict of ``{plugin_id.action_id: ActionSpec}``.
        Returns an empty dict on connection or parse errors.
    """
    session, headers = _connect_to_central_server()
    url = urljoin(CENTRAL_SERVER_URL, "/api/v1/actions/")
    api_response = _safe_central_get(url, session, headers)
    if api_response is None:
        return {}
    try:
        return TypeAdapter(dict[str, ActionSpec]).validate_python(api_response)
    except ValidationError:
        logger.exception("Failed to validate actions response")
        return {}


def execute_action(
    plugin_id: str,
    action_id: str,
    payload: dict | None = None,
    *,
    timeout: float = 30.0,
) -> ActionResult:
    """Execute an action on another plugin via the central server.

    Calls ``POST /api/v1/actions/execute/{plugin_id}/{action_id}``.

    Args:
        plugin_id: ID of the plugin that owns the action (e.g. ``"geoip"``).
        action_id: ID of the action to execute (e.g. ``"locate"``).
        payload: Optional JSON-serialisable dict passed as the request body.
            Typically contains a ``selector`` dict and any action-specific parameters.
        timeout: HTTP timeout in seconds. Defaults to 30.0.

    Returns:
        :class:`~clue.models.actions.ActionResult` from the central server.
        Returns a ``failure`` result on connection or parse errors.
    """
    session, headers = _connect_to_central_server()
    url = urljoin(CENTRAL_SERVER_URL, f"/api/v1/actions/execute/{plugin_id}/{action_id}")
    api_response = _safe_central_post(
        url,
        session,
        headers,
        json_body=payload or {},
        timeout=timeout,
    )
    if api_response is None:
        return ActionResult(
            outcome="failure",
            summary=f"Unable to connect to central server to execute {plugin_id}.{action_id}.",
        )
    try:
        return ActionResult.model_validate(api_response, context={"is_response": True})
    except ValidationError:
        logger.exception("Failed to validate action result for %s.%s", plugin_id, action_id)
        return ActionResult(
            outcome="failure",
            summary=f"Unexpected response format from central server for {plugin_id}.{action_id}.",
        )


def list_fetchers() -> dict[str, FetcherDefinition]:
    """List all fetchers available on the central server for the current user.

    Calls ``GET /api/v1/fetchers/`` and returns a dict keyed by
    ``"<plugin_id>.<fetcher_id>"``, filtered server-side by user classification.

    Returns:
        A dict of ``{plugin_id.fetcher_id: FetcherDefinition}``.
        Returns an empty dict on connection or parse errors.
    """
    session, headers = _connect_to_central_server()
    url = urljoin(CENTRAL_SERVER_URL, "/api/v1/fetchers/")
    api_response = _safe_central_get(url, session, headers)
    if api_response is None:
        return {}
    try:
        return TypeAdapter(dict[str, FetcherDefinition]).validate_python(api_response)
    except ValidationError:
        logger.exception("Failed to validate fetchers response")
        return {}


def run_fetcher(
    plugin_id: str,
    fetcher_id: str,
    selector: Selector,
    *,
    timeout: float = 60.0,
) -> FetcherResult:
    """Execute a fetcher on another plugin via the central server.

    Calls ``POST /api/v1/fetchers/{plugin_id}/{fetcher_id}`` with the provided
    :class:`~clue.models.selector.Selector` as the JSON body.

    Args:
        plugin_id: ID of the plugin that owns the fetcher (e.g. ``"geoip"``).
        fetcher_id: ID of the fetcher to run (e.g. ``"location_report"``).
        selector: The :class:`~clue.models.selector.Selector` to enrich.
        timeout: HTTP timeout in seconds. Defaults to 60.0.

    Returns:
        :class:`~clue.models.fetchers.FetcherResult` from the central server.
        Returns a ``failure`` result on connection or parse errors.
    """
    session, headers = _connect_to_central_server()
    url = urljoin(CENTRAL_SERVER_URL, f"/api/v1/fetchers/{plugin_id}/{fetcher_id}")
    payload = selector.model_dump(exclude_none=True, exclude_unset=True)
    api_response = _safe_central_post(
        url,
        session,
        headers,
        json_body=payload,
        timeout=timeout,
    )
    if api_response is None:
        return FetcherResult.error_result(f"Unable to connect to central server to run {plugin_id}.{fetcher_id}.")
    try:
        return FetcherResult.model_validate(api_response, context={"is_response": True})
    except ValidationError:
        logger.exception("Failed to validate fetcher result for %s.%s", plugin_id, fetcher_id)
        return FetcherResult.error_result(
            f"Unexpected response format from central server for {plugin_id}.{fetcher_id}."
        )
