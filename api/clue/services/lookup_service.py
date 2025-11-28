import functools
import itertools
import json
import math
import os
import time
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any, Optional

from elasticapm.traces import Transaction, capture_span, execution_context
from flask import Request, request
from gevent import Greenlet
from gevent.pool import Pool
from pydantic import BaseModel, ValidationError
from requests import Response, Session
from requests.adapters import HTTPAdapter, Retry

from clue.common.exceptions import (
    AuthenticationException,
    ClueRuntimeError,
    InvalidDataException,
)
from clue.common.logging import get_logger, log_error
from clue.common.logging.audit import audit
from clue.config import CLASSIFICATION as CLASSIFICATION
from clue.config import DEBUG, config
from clue.helper.headers import generate_headers
from clue.models.config import ExternalSource
from clue.models.network import QueryEntry, QueryResult
from clue.models.selector import Selector
from clue.services import auth_service, type_service, user_service

logger = get_logger(__file__)
CLIENTS: dict[str, Session] = {}


def get_client(base_url: str, timeout: float) -> Session:
    """Gets or creates a requests session for the provided base_url.

    Args:
        base_url (str): The base url of the desired client.
        timeout (float): The connection and network timeout to use (is multiplied by 3).

    Returns:
        Session: The requests Session instance matching the provided base_url.
    """
    client_hash = sha256(base_url.encode())
    client_hash.update(str(timeout).encode())
    client_key = client_hash.hexdigest()

    if client_key not in CLIENTS:
        session = Session()
        # Configure connection pool with HTTPAdapter
        pool_connections = math.floor(int(os.environ.get("EXECUTOR_THREADS", 32)) / 2)

        retry_strategy = Retry(
            total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(
            pool_connections=pool_connections, pool_maxsize=pool_connections, max_retries=retry_strategy
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        CLIENTS[client_key] = session

    return CLIENTS[client_key]


def build_result(
    type_name: str, value: str, source: ExternalSource, error: Optional[str] = None, latency: Optional[float] = None
):
    """Builds the QueryResult object using the provided values.

    Args:
        type_name (str): The name of the type of result.
        value (str): The value of the result.
        source (ExternalSource): The ExternalSource that provided the result.
        error (Optional[str], optional): The error that occured during the request. Defaults to None.
        latency (Optional[float], optional): The amount of time between the request and the response (in milliseconds).
            Defaults to None.

    Returns:
        QueryResult: The QueryResult object built.
    """
    if error and error != "invalid_type" and error.lower() != "request timed out":
        logger.warning(error)

    if DEBUG:
        logger.debug("Building query result for source %s", source.name)

    return QueryResult(
        type=type_name,
        value=value,
        source=source.name,
        maintainer=source.maintainer,
        datahub_link=source.datahub_link,
        documentation_link=source.documentation_link,
        error=error,
        latency=latency or 0,
    )


class ParsedParams(BaseModel):
    "Validation of parameters parsed from request"

    query_sources: list[str]
    max_timeout: float
    limit: int
    type_classification: str
    no_annotation: bool
    include_raw: bool
    exclude_unset: bool
    no_cache: bool


def parse_timeout(timeout: float = 5.0) -> float:
    """Gets the max_timeout value from the request object, otherwise uses the provided timeout.

    Args:
        timeout (float, optional): The timeout to use if no max_timeout is provided in the request. Defaults to 5.0.

    Returns:
        float: The parsed max_timeout value.
    """
    try:
        max_timeout = request.args.get("max_timeout", timeout, type=float)
    except (ValueError, TypeError):
        max_timeout = timeout

    return max_timeout


def parse_query_params(request: Request, limit: int = 10, timeout: float = 5.0):
    """Parse the standard query params."""
    query_sources_str = request.args.get("sources")

    limit = request.args.get("limit", limit, type=int)

    type_classification = request.args.get("classification", CLASSIFICATION.UNRESTRICTED)
    no_annotation = request.args.get("no_annotation", "false").lower() in ("true", "1", "")
    no_cache = request.args.get("no_cache", "false").lower() in ("true", "1", "")
    raw = request.args.get("include_raw", "false").lower() in ("true", "1", "")
    exclude_unset = request.args.get("exclude_unset", "false").lower() in ("true", "1", "")

    if query_sources_str:
        if "|" in query_sources_str:
            query_sources = query_sources_str.split("|")
        else:
            query_sources = query_sources_str.split(",")
    else:
        query_sources = []

    return ParsedParams(
        query_sources=query_sources,
        max_timeout=parse_timeout(timeout),
        limit=limit,
        type_classification=type_classification,
        no_annotation=no_annotation,
        include_raw=raw,
        exclude_unset=exclude_unset,
        no_cache=no_cache,
    )


def generate_params(
    limit: int, timeout: float, no_annotation: bool = False, include_raw: bool = False, no_cache: bool = False
) -> dict[str, str | int | float | bool]:
    """Generates HTTP request parameters for a call to a source.

    Args:
        limit (int): The maximum number of results to return.
        timeout (float): The maximum amount of time to wait for a response.
        no_annotation (bool): Whether to include annotations. Defaults to False.
        include_raw (bool): Whether to include the raw results. Defaults to False.
        no_cache (bool): Allows to bypass the cache. Defaults to False.

    Returns:
        str: A string of HTTP params formatted so that it can be appended to a url
            (in the format "?param1=value1&param2=value2")
    """
    params: dict[str, str | int | float | bool] = {
        "limit": limit,
        "max_timeout": max(timeout * 0.95, 0.5),
        "deadline": (datetime.now(timezone.utc) + timedelta(seconds=max(timeout * 0.95, 0.5))).timestamp(),
    }

    if no_annotation:
        params["no_annotation"] = True

    if include_raw:
        params["include_raw"] = True

    if no_cache:
        params["no_cache"] = True

    return params


def process_exception(source_name: str, rsp: Response | None, exception: Exception):
    """Parses an exception in a response.

    Args:
        source_name (str): The name of the source from which the exception came.
        rsp (Response): The response object.
        exception (Exception): The exception to parse.

    Returns:
        str: The formatted string of the parsed exception.
    """
    if isinstance(exception, ConnectionError):
        return f"Could not connect to the specified plugin: {source_name}."

    if rsp and isinstance(exception, json.JSONDecodeError):
        logger.warning("%s: %s", source_name, rsp.status_code)
        if rsp.status_code == 404:
            return None

        if rsp.status_code == 422:
            return f"{source_name} was unable to process this selector."
        elif rsp.status_code > 299:
            return f"{source_name} experienced an unknown error"

    err_msg = f"{source_name} did not return a response in the expected format"
    err_id = log_error(logger, err_msg, exception)

    return f"{err_msg}. Error ID: {err_id}"


def get_sources(user: dict[str, str]):
    """Gets all the sources the user is allowed to submit requests to.

    This must first be checked against what systems the user is allowed to see. Additional type level checking is then
    done later to provide feedback to user.

    Args:
        user (dict[str, Any]): The user for which we want all sources.

    Returns:
        list[ExternalSource]: The sources that the user has access to.
    """
    return [
        x for x in config.api.external_sources if CLASSIFICATION.is_accessible(user["classification"], x.classification)
    ]


def parse_response(source: ExternalSource, user: dict[str, Any], api_response: Any) -> list[QueryEntry]:
    """Parses the response from a source.

    Args:
        source (ExternalSource): The source that returned the response.
        user (dict[str, Any]): The user that initiated the request.
        api_response (Any): The response provided by the source.

    Returns:
        list[QueryEntry]: The list of results contained in the response.
    """
    with capture_span(source.name, "parsing"):
        if isinstance(api_response, dict):
            api_response = [api_response]

        logger.debug(
            "Validating response from source %s, returning %s annotations in %s items",
            source.name,
            len(list(itertools.chain.from_iterable(entry.get("annotations", []) for entry in api_response))),
            len(api_response),
        )

        if source.production:
            logger.debug(f"Skipping validation for production source {source.name}")
            items: list[QueryEntry] = [QueryEntry.model_construct(data) for data in api_response]
        else:
            items = [QueryEntry.model_validate(data, context={"user": user}) for data in api_response]

        return items


def parse_bulk_response(
    source: ExternalSource,
    user: dict[str, Any],
    api_response: dict[str, dict[str, Any]],
    latency: Optional[float] = None,
) -> dict[str, dict[str, QueryResult]]:
    """Parses the response from a bulk request to a source.

    Args:
        source (ExternalSource): The source that returned the response.
        user (dict[str, Any]): The user that initiated the request.
        api_response (dict[str, dict[str, Any]]): The response provided by the source.
        latency (Optional[float]): The time between the request and the response, in milliseconds.

    Returns:
        dict[str, dict[str, QueryResult]]: A dict containing each type and their corresponding result sets.
    """
    bulk_result: dict[str, dict[str, QueryResult]] = {}

    if source.production:
        logger.debug(f"Skipping validation for production source {source.name}")

    with capture_span(f"{source.name}-bulk", "parsing"):
        for type in api_response:
            bulk_result.setdefault(type, {})
            for value in api_response[type]:
                data: dict[str, Any] = dict(
                    type=type,
                    value=value,
                    source=source.name,
                    maintainer=source.maintainer,
                    datahub_link=source.datahub_link,
                    documentation_link=source.documentation_link,
                )

                # This allows plugins to overwrite the default values if they want
                data = {**data, **api_response[type][value], "latency": latency or 0.0}

                logger.debug(
                    "Validating bulk response from source %s (%s), returning %s annotations in %s items, using user %s",
                    source.name,
                    "production" if source.production else "not production",
                    len(
                        list(
                            itertools.chain.from_iterable(
                                entry.get("annotations", []) for entry in data.get("items", [])
                            )
                        )
                    ),
                    len(data.get("items", [])),
                    user.get("uname", user.get("email", None)),
                )

                if source.production:
                    bulk_result[type][value] = QueryResult.model_construct(**data)
                else:
                    bulk_result[type][value] = QueryResult.model_validate(
                        data,
                        context={"user": user},
                    )

        return bulk_result


def handle_validation_error(source: ExternalSource, err: ValidationError) -> str:
    """Handles errors that occured while trying to parse a response from a source.

    Args:
        source (ExternalSource): The source from which the invalid response came.
        err (ValidationError): The error in question.

    Returns:
        str: A formatted error message.
    """
    pydantic_errs: list[str] = []

    for validation_err in err.errors():
        loc = ".".join(
            section if isinstance(section, str) else f"[{str(section)}]" for section in validation_err["loc"]
        )
        pydantic_errs.append(f'"{loc}": {validation_err["msg"]}')

    err_msg = f"{source.name} returned an improperly formatted response: {', '.join(pydantic_errs)}"
    err_id = log_error(logger, err_msg, err)
    return f"{err_msg}. Error ID: {err_id}"


def query_external(
    user: dict[str, Any],
    source: ExternalSource,
    type_name: str,
    value: str,
    limit: int,
    timeout: float,
    access_token: str,
    clue_access_token: str | None,
    no_annotation: bool = False,
    no_cache: bool = False,
    include_raw: bool = True,
    apm_transaction: Optional[Transaction] = None,
) -> Optional[QueryResult]:
    """Query the external source for details."""
    if apm_transaction:
        execution_context.set_transaction(apm_transaction)

    finish_result = functools.partial(build_result, type_name, value, source)

    with capture_span(query_external.__name__, span_type="greenlet"):
        if type_name not in type_service.all_supported_types(user, access_token=access_token).get(source.name, {}):
            return finish_result(error="invalid_type")

        if config.api.audit:
            audit(
                [
                    f"source={source.name}",
                    f"type={type_name}",
                    f"value={value}",
                    f"no_annotation={no_annotation}",
                    f"include_raw={include_raw}",
                    f"no_cache={no_cache}",
                ],
                {},
                user,
                query_external,
            )

        if quota_error := user_service.check_quota(source, user):
            return finish_result(error=quota_error)

        # perform the lookup, ensuring access controls are applied
        url = f"{source.url}/lookup/{type_name}/{value}/"
        response: Any = None
        rsp: Response | None = None
        start = time.perf_counter()
        try:
            with capture_span(url, "http"):
                rsp = get_client(source.url, timeout).get(
                    url,
                    params=generate_params(limit, timeout, no_annotation, include_raw, no_cache),
                    headers=generate_headers(access_token, clue_access_token),
                    timeout=(timeout, timeout * 3),
                )
                rsp.raise_for_status()

            response = rsp.json()
        except Exception as exception:
            return finish_result(
                error=process_exception(source.name, rsp, exception),
                latency=(time.perf_counter() - start) * 1000,
            )
        finally:
            user_service.release_quota(source, user)

        if response and "api_error_message" in response and response["api_error_message"]:
            logger.warning(f"Error response from {url}: {response['api_error_message']}")
            return finish_result(
                error=response["api_error_message"],
                latency=(time.perf_counter() - start) * 1000,
            )

        try:
            result = finish_result(latency=(time.perf_counter() - start) * 1000)

            api_response = response["api_response"]
            if api_response:
                result.items = parse_response(source, user, api_response)

            logger.debug("Returning valid result from source %s", source)

            return result
        except ValidationError as err:
            logger.exception("Validation error on response from %s", source)
            return finish_result(
                error=handle_validation_error(source, err),
                latency=(time.perf_counter() - start) * 1000,
            )


def enrich(type_name: str, value: str, user: dict[str, Any]):  # noqa: C901
    """Queries all available sources with the provided value.

    Args:
        type_name (str): The type of the value to query.
        value (str): The value to query.
        user (dict[str, Any]): The user requesting the query.

    Raises:
        AuthenticationException: Raised whenever there is a problem with the authentication.

    Returns:
        dict[str, QueryResult]: A dict of each source and their query result.
    """
    query_params = parse_query_params(request=request)
    query_sources = query_params.query_sources
    available_sources = get_sources(user)

    access_token = request.headers.get("Authorization", type=str)
    if not access_token:
        raise AuthenticationException("Access token is required to enrich.")
    access_token = access_token.split(" ")[1]

    logger.debug(
        f"Beginning enrichment for single selector on sources "
        f"[{','.join(query_sources or [source.name for source in available_sources])}]"
    )

    results: dict[str, QueryResult] = {}

    pool_size = min(len(query_sources or available_sources), int(os.environ.get("EXECUTOR_THREADS", 32)))
    thread_pool = Pool(pool_size)

    greenlets: list[tuple[str, str, ExternalSource, Greenlet[Any, Optional[QueryResult]]]] = []
    # create searches for external sources
    for source in available_sources:
        if query_sources and source.name not in query_sources:
            continue
        elif not query_sources and not source.include_default:
            continue

        finish_result = functools.partial(build_result, type_name, value, source)

        obo_access_token, error = auth_service.check_obo(source, access_token, user["uname"])

        # TODO: sa-clue support
        if not obo_access_token and source.obo_target:
            results[source.name] = finish_result(error="You must have a valid JWT to access this plugin.")
            continue

        if error:
            results[source.name] = finish_result(error=error)
            continue

        # check query against the max supported classification of the external system
        # if this is not supported, we should let the user know.
        if not CLASSIFICATION.is_accessible(
            source.max_classification or CLASSIFICATION.UNRESTRICTED, query_params.type_classification
        ):
            results[source.name] = finish_result(
                error=f"Type classification exceeds max classification of source: {source.name}."
            )
            continue

        greenlets.append(
            (
                type_name,
                value,
                source,
                thread_pool.spawn(
                    query_external,
                    user=user,
                    source=source,
                    type_name=type_name,
                    value=value,
                    limit=query_params.limit,
                    timeout=query_params.max_timeout,
                    access_token=obo_access_token or access_token,
                    clue_access_token=access_token if obo_access_token else None,
                    no_annotation=query_params.no_annotation,
                    include_raw=query_params.include_raw,
                    no_cache=query_params.no_cache,
                    apm_transaction=execution_context.get_transaction(),
                ),
            )
        )

    thread_pool.join(timeout=query_params.max_timeout * 2)

    for type_name, value, source, greenlet in greenlets:
        result = greenlet.value
        if result:
            if result.error == "invalid_type":
                continue

            results[source.name] = result
        else:
            results[source.name] = build_result(
                type_name, value, source, "Request Timed Out" if not greenlet.exception else str(greenlet.exception)
            )

    thread_pool.kill(block=False)

    return results


def bulk_query_external(  # noqa: C901
    data: list[Selector],
    user: dict[str, Any],
    source: ExternalSource,
    limit: int,
    timeout: float,
    access_token: str,
    clue_access_token: str | None,
    no_annotation: bool = False,
    no_cache: bool = False,
    include_raw: bool = True,
    apm_transaction: Optional[Transaction] = None,
) -> dict[str, dict[str, QueryResult]]:
    """Query the external source for details."""
    if apm_transaction:
        execution_context.set_transaction(apm_transaction)

    with capture_span(bulk_query_external.__name__, span_type="greenlet"):
        supported_types = type_service.all_supported_types(user, access_token=access_token).get(source.name, {})
        bulk_result: dict[str, dict[str, QueryResult]] = {}

        filtered_data: list[Selector] = []
        for entry in data:
            bulk_result.setdefault(entry.type, {})

            if entry.type not in supported_types:
                bulk_result[entry.type][entry.value] = build_result(entry.type, entry.value, source, "invalid_type")
                continue

            filtered_data.append(entry)

        data = filtered_data

        if config.api.audit:
            values = ",".join(f"{entry.type}:{entry.value}" for entry in data)

            audit(
                [
                    f"source={source.name}",
                    f"values={values}",
                    f"no_annotation={no_annotation}",
                    f"include_raw={include_raw}",
                    f"no_cache={no_cache}",
                ],
                {},
                user,
                bulk_query_external,
            )

        if quota_error := user_service.check_quota(source, user):
            for entry in data:
                bulk_result.setdefault(entry.type, {})
                bulk_result[entry.type][entry.value] = build_result(entry.type, entry.value, source, error=quota_error)

            return bulk_result

        # perform the lookup, ensuring access controls are applied
        error = None
        latency = None

        url = f"{source.url}/lookup/"
        response: Any = None
        start = time.perf_counter()
        rsp: Response | None = None
        try:
            with capture_span(url, "http"):
                rsp = get_client(source.url, timeout).post(
                    url,
                    params=generate_params(limit, timeout, no_annotation, include_raw, no_cache),
                    json=[entry.model_dump(exclude_none=True, exclude_unset=True) for entry in data],
                    headers=generate_headers(access_token, clue_access_token),
                    timeout=(timeout * 3, timeout * 3),
                )
                rsp.raise_for_status()

            if not rsp:
                raise ClueRuntimeError(f"An error occurred when connecting to {source.name}.")  # noqa: TRY301

            logger.debug(f"{rsp.status_code}: {url}")
            response = rsp.json()
        except Exception as exception:
            error = process_exception(source.name, rsp, exception)
        finally:
            end = time.perf_counter()
            latency = (end - start) * 1000

        if response and "api_error_message" in response and response["api_error_message"]:
            error = response["api_error_message"]

        if error:
            for entry in data:
                bulk_result[entry.type][entry.value] = build_result(
                    entry.type, entry.value, source, error=error, latency=latency
                )

            return bulk_result

        try:
            api_response = response["api_response"]
            # handle case of 200 OK for not found.
            if not api_response:
                for entry in data:
                    bulk_result[entry.type][entry.value] = build_result(
                        entry.type, entry.value, source, latency=latency
                    )
            else:
                bulk_result = parse_bulk_response(source, user, api_response, latency)
        except ValidationError as err:
            error_message = handle_validation_error(source, err)

            for entry in data:
                bulk_result[entry.type][entry.value] = build_result(
                    entry.type, entry.value, source, error=error_message, latency=latency
                )

        return bulk_result


def bulk_enrich(data: list[Selector], user: dict[str, Any]):  # noqa: C901
    """create searches for external sources"""
    query_params = parse_query_params(request=request)
    query_sources = query_params.query_sources
    available_sources = get_sources(user)

    logger.debug(
        f"Beginning enrichment for {len(data)} selectors on sources "
        f"[{','.join(query_sources or [source.name for source in available_sources])}]"
    )

    access_token = request.headers.get("Authorization", type=str)
    if not access_token:
        raise AuthenticationException("Access token is required to enrich.")
    access_token = access_token.split(" ")[1]

    if len(data) < 1:
        raise InvalidDataException("You must provide at least one value to lookup.")

    bulk_result: dict[str, dict[str, dict[str, QueryResult]]] = {}
    for entry in data:
        bulk_result.setdefault(entry.type, {})
        bulk_result[entry.type].setdefault(entry.value, {})

    pool_size = min(len(data) * len(query_sources or available_sources), int(os.environ.get("EXECUTOR_THREADS", 32)))
    thread_pool = Pool(pool_size)

    greenlets: list[tuple[list[Selector], ExternalSource, Greenlet[Any, dict[str, dict[str, QueryResult]]]]] = []
    for source in available_sources:
        if query_sources and source.name not in query_sources:
            continue
        elif not query_sources and not source.include_default:
            continue

        obo_access_token, error = auth_service.check_obo(source, access_token, user["uname"])

        if error:
            logger.error("%s: %s", source.name, error)

        # TODO: sa-clue support
        if not obo_access_token and source.obo_target:
            for entry in data:
                bulk_result[entry.type][entry.value][source.name] = build_result(
                    entry.type, entry.value, source, "You must have a valid JWT to access this plugin."
                )
            continue

        data_for_source: list[Selector] = []

        # check query against the max supported classification of the external system
        # if this is not supported, we should let the user know.
        for entry in data:
            if entry.sources is not None and source.name not in entry.sources:
                continue

            if not CLASSIFICATION.is_accessible(
                source.max_classification or CLASSIFICATION.UNRESTRICTED,
                entry.classification,
            ):
                if source.name in (entry.sources or []):
                    bulk_result[entry.type][entry.value][source.name] = build_result(
                        entry.type,
                        entry.value,
                        source,
                        (
                            f"Selector classification ({entry.classification}) exceeds max classification "
                            f"of source: {source.name} ({source.max_classification})."
                        ),
                    )

                continue

            data_for_source.append(entry)

        greenlets.append(
            (
                data_for_source,
                source,
                thread_pool.spawn(
                    bulk_query_external,
                    data=data_for_source,
                    user=user,
                    source=source,
                    limit=query_params.limit,
                    timeout=query_params.max_timeout,
                    access_token=obo_access_token or access_token,
                    clue_access_token=access_token if obo_access_token else None,
                    no_annotation=query_params.no_annotation,
                    no_cache=query_params.no_cache,
                    include_raw=query_params.include_raw,
                    apm_transaction=execution_context.get_transaction(),
                ),
            )
        )

    start = time.perf_counter()

    thread_pool.join(timeout=query_params.max_timeout * 2.2)

    for greenlet_data, source, greenlet in greenlets:
        result = greenlet.value

        if not result:
            for entry in greenlet_data:
                bulk_result[entry.type][entry.value][source.name] = build_result(
                    entry.type,
                    entry.value,
                    source,
                    "Request Timed Out" if not greenlet.exception else str(greenlet.exception),
                    (time.perf_counter() - start) * 1000,
                )

            continue

        for type, values in result.items():
            for value, query_result in values.items():
                if result[type][value].error == "invalid_type":
                    continue

                bulk_result[type][value][source.name] = query_result

    thread_pool.kill(block=False)

    return bulk_result
