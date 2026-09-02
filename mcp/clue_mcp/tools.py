from logging import getLogger
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import quote

from fastmcp.server.dependencies import get_access_token, get_http_request
from mcp.server.auth.provider import AccessToken
from pydantic import BaseModel, Field

from clue_mcp.api import ClueApiClient

logger = getLogger(__name__)


class Selector(BaseModel):
    """Typed value sent to a Clue action, fetcher, or enrichment lookup."""

    type: str = Field(description="Clue data type, such as ipv4, domain, sha256, or telemetry.")
    value: str = Field(description="Value to process. Telemetry values must contain a JSON object string.")
    classification: str | None = Field(default=None, description="Classification assigned to this value.")
    sources: list[str] | None = Field(default=None, description="Sources to include or exclude for enrichment.")


class EnrichmentOptions(BaseModel):
    """Optional query parameters supported by Clue enrichment endpoints."""

    classification: str | None = Field(default=None, description="Maximum classification to return.")
    sources: list[str] | None = Field(
        default=None,
        description="Source IDs to include; prefix an ID with '-' to exclude it.",
    )
    max_timeout: float | None = Field(default=None, gt=0, description="Maximum execution time in seconds.")
    limit: int | None = Field(default=None, ge=1, description="Maximum results returned per source.")
    no_annotation: bool | None = Field(default=None, description="Omit annotations from results.")
    no_cache: bool | None = Field(default=None, description="Bypass cached plugin results.")
    include_raw: bool | None = Field(default=None, description="Include raw plugin data.")
    exclude_unset: bool | None = Field(default=None, description="Omit values not set by a plugin.")


def register_tools(mcp, api_client: ClueApiClient):
    """Register all Clue MCP tools on the provided FastMCP instance.

    Args:
        mcp: FastMCP server instance used to register tool handlers.
        api_client: Shared API client used by tools to call the Clue backend.
    """

    def _route_segment(value: str, label: str) -> str:
        """Validate and encode one API route segment."""
        if (
            not value
            or any(character in value for character in "/\\")
            or any(ord(character) < 32 for character in value)
        ):
            raise ValueError(f"{label} must be a non-empty route segment")
        return quote(value, safe="")

    def _documentation_path(filename: str) -> str:
        """Validate and encode a relative documentation path."""
        path = PurePosixPath(filename)
        if (
            not filename
            or path.is_absolute()
            or any(part in {"", ".", ".."} for part in path.parts)
            or "\\" in filename
        ):
            raise ValueError("filename must be a non-empty relative path without traversal segments")
        return "/".join(quote(part, safe="") for part in path.parts)

    def _enrichment_params(options: EnrichmentOptions | None) -> dict[str, Any] | None:
        """Convert MCP enrichment options to Clue query parameters."""
        if options is None:
            return None
        params = options.model_dump(exclude_none=True)
        if sources := params.get("sources"):
            params["sources"] = "|".join(sources)
        return params

    def _request_timeout(max_timeout: float | None) -> float | None:
        """Allow the backend timeout plus time for HTTP transport overhead."""
        if max_timeout is None:
            return None
        if max_timeout <= 0:
            raise ValueError("max_timeout must be greater than zero")
        return max_timeout

    def _proper_access_token() -> AccessToken:
        """Return the current request access token or fail consistently."""
        request_available = False
        scope_user_available = False
        scope_token_type = "NoneType"
        auth_header_present = False
        request_path = "unknown"
        scope_access_token: Any = None

        try:
            request = get_http_request()
            # was not able to get request
            if not request:
                raise ValueError("request was receive empty")
            request_available = True

            scope_user = request.scope.get("user")
            # was not able to get user scope
            if not scope_user:
                raise ValueError("request did not contain the scope user")
            scope_user_available = True

            scope_access_token = getattr(scope_user, "access_token", None)
            scope_token_type = type(scope_access_token).__name__
            auth_header_present = bool(request.headers.get("authorization"))

            request_path = request.url.path
        except RuntimeError as e:
            logger.warning(f"auth_context_probe_failed error={e}")
        except ValueError as e:
            logger.warning(f"Server did not answer properly : {e}")

        access_token: AccessToken | None = None
        error: str = ""
        try:
            access_token = get_access_token()
        except (ValueError, TypeError) as e:
            # FastMCP may fail internal type checks even when request.scope.user
            # is present. Recover using the raw token value from the request
            # scope; only ``token`` is used downstream by ClueApiClient.
            error = str(e)
            token_value = getattr(scope_access_token, "token", None)
            if token_value:
                access_token = AccessToken(
                    token=token_value,
                    client_id=getattr(scope_access_token, "client_id", "unknown-client"),
                    scopes=list(getattr(scope_access_token, "scopes", [])),
                    expires_at=getattr(scope_access_token, "expires_at", None),
                    resource=getattr(scope_access_token, "resource", None),
                )

        # get_access_token may return None without raising (expired background-task snapshot)
        if not access_token:
            raise ValueError(
                "Access token is not available. "
                f"request_available={request_available} "
                f"scope_user_available={scope_user_available} "
                f"scope_token_available={scope_access_token is not None} "
                f"scope_token_type={scope_token_type} "
                f"auth_header_present={auth_header_present} "
                f"request_path={request_path} "
                f"upstream_error={error}"
            )

        return access_token

    # region actions
    @mcp.tool(name="get_actions")
    async def get_actions() -> dict:
        """Return the actions supported by configured external services.

        Returns:
            dict: Actions keyed by ``<plugin_id>.<action_id>``. Each value
            describes the action, including its name, classification, summary,
            supported types, and parameter schema.

        Raises:
            ValueError: If an access token is not available.
            httpx.HTTPError: If the Clue API request fails.
        """
        return await api_client.call(
            user_access_token=_proper_access_token(),
            path="actions/",
            method="GET",
            body=None,
        )

    @mcp.tool(name="execute_action")
    async def execute_action(
        plugin_id: str,
        action_id: str,
        selectors: list[Selector] | None = None,
        selector: Selector | None = None,
        context: dict[str, Any] | None = None,
        parameters: dict[str, Any] | None = None,
        max_timeout: float | None = None,
    ) -> dict[str, Any]:
        """Execute an external-service action for one or more values.

        Args:
            plugin_id: ID of the plugin that provides the action.
            action_id: ID of the action to execute.
            selectors: Values supplied to an action that accepts multiple inputs.
            selector: Value supplied to an action that accepts one input.
            context: Optional execution context accepted by the action.
            parameters: Additional top-level fields required by the action's parameter schema.
            max_timeout: Optional backend request timeout in seconds if not input, will use the setup timeout from config file.

        Returns:
            dict: The action result, including its outcome, output format,
            output value, and a task ID when execution is still pending.

        Raises:
            ValueError: If an access token is not available.
            httpx.HTTPError: If the Clue API request fails.
        """
        body = dict(parameters or {})
        reserved_fields = {"selector", "selectors", "context"} & body.keys()
        max_timeout = _request_timeout(max_timeout)
        if reserved_fields:
            fields = ", ".join(sorted(reserved_fields))
            raise ValueError(f"parameters must not override reserved fields: {fields}")
        if selectors is not None:
            body["selectors"] = [item.model_dump(exclude_none=True) for item in selectors]
        if selector is not None:
            body["selector"] = selector.model_dump(exclude_none=True)
        if context is not None:
            body["context"] = context

        return await api_client.call(
            user_access_token=_proper_access_token(),
            path=f"actions/execute/{_route_segment(plugin_id, 'plugin_id')}/{_route_segment(action_id, 'action_id')}",
            method="POST",
            body=body,
            params={"max_timeout": max_timeout} if max_timeout is not None else None,
            request_timeout=max_timeout,
        )

    @mcp.tool(name="get_action_status")
    async def get_action_status(
        plugin_id: str,
        action_id: str,
        task_id: str,
        max_timeout: float | None = None,
    ) -> dict[str, Any]:
        """Return the status or result of a running action.

        Args:
            plugin_id: ID of the plugin that provides the action.
            action_id: ID of the action whose status should be retrieved.
            task_id: ID of the specific action task to retrieve.
            max_timeout: Optional backend request timeout in seconds if not input, will use the setup timeout from config file.

        Returns:
            dict: The action result, including an outcome of ``success``,
            ``failure``, or ``pending``, its output format and value, and the
            task ID when execution remains pending.

        Raises:
            ValueError: If an access token is not available.
            httpx.HTTPError: If the Clue API request fails.
        """
        max_timeout = _request_timeout(max_timeout)
        return await api_client.call(
            user_access_token=_proper_access_token(),
            path=(
                f"actions/{_route_segment(plugin_id, 'plugin_id')}/{_route_segment(action_id, 'action_id')}"
                f"/status/{_route_segment(task_id, 'task_id')}"
            ),
            method="GET",
            body=None,
            params={"max_timeout": max_timeout} if max_timeout is not None else None,
            request_timeout=_request_timeout(max_timeout),
        )

    # region fetchers

    @mcp.tool(name="get_fetchers")
    async def get_fetchers() -> dict:
        """Return the fetchers supported by configured external services.

        Returns:
            dict: Fetchers keyed by ``<plugin_id>.<fetcher_id>``. Each value
            describes the fetcher, including its classification, description,
            output format, supported data types, and whether it runs
            asynchronously.

        Raises:
            ValueError: If an access token is not available.
            httpx.HTTPError: If the Clue API request fails.
        """
        return await api_client.call(
            user_access_token=_proper_access_token(), path="fetchers/", method="GET", body=None
        )

    @mcp.tool(name="run_fetcher")
    async def run_fetcher(
        plugin_id: str,
        fetcher_id: str,
        selector: Selector,
        max_timeout: float | None = None,
    ) -> dict[str, Any]:
        """Run an external-service fetcher for a typed data value.

        Args:
            plugin_id: ID of the plugin that provides the fetcher.
            fetcher_id: ID of the fetcher to run.
            selector: Typed value on which to run the fetcher.
            max_timeout: Optional backend request timeout in seconds if not input, will use the setup timeout from config file.

        Returns:
            dict: The fetcher result, including its outcome and, depending on
            that outcome, returned data, an error, its output format, a link,
            or a task ID when execution is pending.

        Raises:
            ValueError: If an access token is not available.
            httpx.HTTPError: If the Clue API request fails.
        """
        max_timeout = _request_timeout(max_timeout)
        return await api_client.call(
            user_access_token=_proper_access_token(),
            path=f"fetchers/{_route_segment(plugin_id, 'plugin_id')}/{_route_segment(fetcher_id, 'fetcher_id')}",
            method="POST",
            body=selector.model_dump(exclude_none=True),
            params={"max_timeout": max_timeout} if max_timeout is not None else None,
            request_timeout=_request_timeout(max_timeout),
        )

    @mcp.tool(name="get_fetcher_status")
    async def get_fetcher_status(
        plugin_id: str,
        fetcher_id: str,
        task_id: str,
        max_timeout: float | None = None,
    ) -> dict[str, Any]:
        """Return the status or result of a running fetcher.

        Args:
            plugin_id: ID of the plugin that provides the fetcher.
            fetcher_id: ID of the fetcher whose status should be retrieved.
            task_id: ID of the specific fetcher task to retrieve.
            max_timeout: Optional backend request timeout in seconds if not input, will use the setup timeout from config file.

        Returns:
            dict: The fetcher result, including an outcome of ``success``,
            ``failure``, or ``pending`` and any returned data, error, output
            format, link, or pending task ID.

        Raises:
            ValueError: If an access token is not available.
            httpx.HTTPError: If the Clue API request fails.
        """
        max_timeout = _request_timeout(max_timeout)
        return await api_client.call(
            user_access_token=_proper_access_token(),
            path=(
                f"fetchers/{_route_segment(plugin_id, 'plugin_id')}/{_route_segment(fetcher_id, 'fetcher_id')}"
                f"/status/{_route_segment(task_id, 'task_id')}"
            ),
            method="GET",
            params={"max_timeout": max_timeout} if max_timeout is not None else None,
            request_timeout=_request_timeout(max_timeout),
        )

    # region lookup

    @mcp.tool(name="get_types")
    async def get_types() -> dict:
        """Return the data types supported by each external service.

        Returns:
            dict: Supported type names grouped by external source name.

        Raises:
            ValueError: If an access token is not available.
            httpx.HTTPError: If the Clue API request fails.
        """
        return await api_client.call(user_access_token=_proper_access_token(), path="lookup/types/", method="GET")

    @mcp.tool(name="get_types_detection")
    async def get_types_detection() -> dict:
        """Return regular expressions used to detect supported data types.

        Returns:
            dict: Regular-expression patterns keyed by data type name.

        Raises:
            ValueError: If an access token is not available.
            httpx.HTTPError: If the Clue API request fails.
        """
        return await api_client.call(
            user_access_token=_proper_access_token(),
            path="lookup/types_detection/",
            method="GET",
        )

    @mcp.tool(name="bulk_enrich")
    async def bulk_enrich(
        data: list[Selector],
        options: EnrichmentOptions | None = None,
    ) -> dict[str, Any]:
        """Enrich multiple typed values through configured external sources.

        Args:
            data: Selectors to enrich. Each selector must contain ``type`` and
                ``value`` and may include ``classification`` and ``sources``.
            options: Optional filtering, timeout, cache, and output controls.
        Returns:
            dict: Enrichment results grouped by data type, value, and external
            source.

        Raises:
            ValueError: If an access token is not available.
            httpx.HTTPError: If the Clue API request fails.
        """
        return await api_client.call(
            user_access_token=_proper_access_token(),
            path="lookup/enrich",
            method="POST",
            body=[selector.model_dump(exclude_none=True) for selector in data],
            params=_enrichment_params(options),
            request_timeout=_request_timeout(options.max_timeout if options is not None else None),
        )

    @mcp.tool(name="enrich")
    async def enrich(
        type_name: str,
        value: str,
        options: EnrichmentOptions | None = None,
    ) -> dict[str, Any]:
        """Enrich one typed value through configured external sources.

        Args:
            type_name: Type of value to enrich, such as ``ipv4`` or ``domain``.
            value: Value to enrich. URL encoding is handled by this tool.
            options: Optional filtering, timeout, cache, and output controls.

        Returns:
            dict: Enrichment results keyed by external source name.

        Raises:
            ValueError: If an access token is not available.
            httpx.HTTPError: If the Clue API request fails.
        """
        return await api_client.call(
            user_access_token=_proper_access_token(),
            path=f"lookup/enrich/{_route_segment(type_name, 'type_name')}/{quote(quote(value, safe=''), safe='')}/",
            method="GET",
            params=_enrichment_params(options),
            request_timeout=_request_timeout(options.max_timeout if options is not None else None),
        )

    # region static

    @mcp.tool(name="serve_documentation")
    async def serve_documentation(documentation_filter: str | None = None) -> dict:
        """Return available Clue documentation as Markdown.

        Args:
            documentation_filter: Optional text used to include only documents
                whose filenames contain the supplied value.

        Returns:
            dict: Markdown document contents keyed by filename. An empty
            dictionary is returned when no filenames match the filter.

        Raises:
            ValueError: If an access token is not available.
            httpx.HTTPError: If the Clue API request fails.
        """
        return await api_client.call(
            user_access_token=_proper_access_token(),
            path="static/docs",
            method="GET",
            params={"filter": documentation_filter} if documentation_filter is not None else None,
        )

    @mcp.tool(name="serve_documentation_file")
    async def serve_documentation_file(filename: str) -> dict:
        """Return one Clue documentation file as Markdown.

        Args:
            filename: Filename or relative documentation path to retrieve,
                including its extension.

        Returns:
            dict: A dictionary containing the document text under the
            ``markdown`` key.

        Raises:
            ValueError: If an access token is not available.
            httpx.HTTPStatusError: If the file does not exist, its path is
                invalid, or the Clue API returns another error response.
            httpx.HTTPError: If the Clue API request otherwise fails.
        """
        return await api_client.call(
            user_access_token=_proper_access_token(),
            path=f"static/docs/{_documentation_path(filename)}",
            method="GET",
        )
