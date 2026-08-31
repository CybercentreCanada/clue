import re
from logging import getLogger
from typing import Any

import httpx
from fastmcp.server.dependencies import get_access_token, get_http_request
from mcp.server.auth.provider import AccessToken
from pydantic import BaseModel, Field

from clue_mcp.api import ClueApiClient
from clue_mcp.config import CLUE_UI, ICONIFY

# Safety limits to avoid oversized backend requests.
MAXIMUM_TICKET: int = 200
MAXIMUM_OFFSET: int = 10000
# Reject ASCII control characters and path separators in path-bound
# identifiers such as hit_id.
CONTROL_OR_PATH_SEP_PATTERN = re.compile(r"[\x00-\x1F\x7F/\\]")

# Dossier update allowed keys
PERMITTED_KEYS = {
    "title",
    "query",
    "leads",
    "pivots",
    "type",
    "owner",
}
# supported languages
INTENDED_LANGUAGE: set = {"en", "fr"}

logger = getLogger(__name__)


class WhoAmIResponse(BaseModel):
    username: str = Field(description="Unique login name used to identify the current user in Clue.")
    email: str = Field(description="Primary email address associated with the user account.")
    groups: list[str] = Field(
        default_factory=list,
        description="Security or organizational groups the user belongs to.",
    )
    roles: list[str] = Field(
        default_factory=list,
        description="Application roles granted to the user, such as admin or user.",
    )


# Structured response envelope returned by ``lucene_query``.
class ClueResponse(BaseModel):
    rows: int = Field(description="Number of rows returned in the search results.")
    total: int = Field(description="Total number of hits matching the search criteria.")
    hits: list[dict[str, Any]] = Field(default_factory=list, description="List of hits matching the search criteria.")


def register_tools(mcp, api_client: ClueApiClient):
    """Register all Clue MCP tools on the provided FastMCP instance.

    Args:
        mcp: FastMCP server instance used to register tool handlers.
        api_client: Shared API client used by tools to call the Clue backend.
    """
    # Cache searchable fields for this process to reduce mapping calls.
    cached_hit_fields: set[str] | None = None

    def _contains_escape_characters(value: str) -> bool:
        """Return True when value contains control chars or path separators."""
        return bool(CONTROL_OR_PATH_SEP_PATTERN.search(value))

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
            path="action/",
            method="GET",
            body=None,
        )

    @mcp.tool(name="execute_action")
    async def execute_action(plugin_id:str, action_id:str, task_id:str, type:str,value:str) -> dict:
        """Execute an external-service action for a data value.

        Args:
            plugin_id: ID of the plugin that provides the action.
            action_id: ID of the action to execute.
            task_id: ID used to identify the action task.
            type: Type of data supplied to the action, such as ``ip``.
            value: Data value on which to execute the action.

        Returns:
            dict: The action result, including its outcome, output format,
            output value, and a task ID when execution is still pending.

        Raises:
            ValueError: If an access token is not available.
            httpx.HTTPError: If the Clue API request fails.
        """
        return await api_client.call(
            user_access_token=_proper_access_token(),
            path= f'action/{plugin_id}/{action_id}/status/{task_id}',
            method= "POST",
            body={
                "type":type,
                "value":value
            }
        )

    @mcp.tool(name="get_action_status")
    async def get_action_status(plugin_id:str, action_id:str, task_id:str) -> dict:
        """Return the status or result of a running action.

        Args:
            plugin_id: ID of the plugin that provides the action.
            action_id: ID of the action whose status should be retrieved.
            task_id: ID of the specific action task to retrieve.

        Returns:
            dict: The action result, including an outcome of ``success``,
            ``failure``, or ``pending``, its output format and value, and the
            task ID when execution remains pending.

        Raises:
            ValueError: If an access token is not available.
            httpx.HTTPError: If the Clue API request fails.
        """
        return await api_client.call(
            user_access_token=_proper_access_token(),
            path = f"action/{plugin_id}/{action_id}/status/{task_id}",
            method="GET",
            body=None
        )