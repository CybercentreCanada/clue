import os
from typing import Any, cast

from flask import request
from requests import Session
from trino.auth import JWTAuthentication
from trino.dbapi import Connection, Cursor

from clue.common.exceptions import ClueValueError
from clue.common.logging import get_logger
from clue.plugin.helpers.token import get_username

logger = get_logger(__file__)


def get_trino_connection(
    connections: dict[str, Connection],
    source: str | None = None,
    request_timeout: int = 60,
    max_attempts: int = 2,
    username_claims: list[str] | None = None,
    access_token: str | None = None,
    host: str | None = None,
    session: Session | None = None,
) -> Connection:
    """Get a Trino database connection authenticated with a JWT token.

    This function creates or retrieves a cached Trino connection using JWT authentication.
    Connections are cached by JWT token to avoid recreating them unnecessarily, unless
    a custom session is provided.

    Args:
        connections: Dictionary storing cached connections keyed by JWT token
        source: Application identifier for the connection (defaults to APP_NAME env var)
        request_timeout: Timeout in seconds for Trino requests (default: 60)
        max_attempts: Maximum number of retry attempts for failed requests (default: 2)
        username_claims: List of JWT claims to extract username from (optional)
        access_token: JWT token for authentication (defaults to Authorization header)
        host: Trino server hostname (defaults to TRINO_HOST env var)
        session: Custom requests.Session object for connection pooling (optional)

    Returns:
        Connection: An authenticated Trino connection object

    Raises:
        ClueValueError: If required host or source parameters are missing

    Note:
        - Connections with custom sessions are not cached
        - Legacy prepared statements are disabled to reduce load on Trino
    """
    if not host and "TRINO_HOST" not in os.environ:
        raise ClueValueError("You must specify a host, or there must be a TRINO_HOST environment variable.")

    if not source and "APP_NAME" not in os.environ:
        raise ClueValueError("You must specify a source, or there must be an APP_NAME environment variable.")

    # Extract JWT token from provided access_token or Authorization header (format: "Bearer <token>")
    jwt_token: str = access_token or cast(str, request.headers.get("Authorization", None, type=str)).split(" ")[1]

    # Create new connection if not cached or if using a custom session
    if jwt_token not in connections or session is not None:
        new_connection = Connection(
            http_scheme="https",
            host=host or os.environ["TRINO_HOST"],
            port=int(os.environ.get("TRINO_PORT", "443")),
            user=get_username(jwt_token, claims=username_claims),
            auth=JWTAuthentication(jwt_token),
            source=source or f"clue-{os.environ["APP_NAME"]}",
            max_attempts=max_attempts,
            request_timeout=request_timeout,
            http_session=session,
            # This will stop trino from being bombarded with EXECUTE IMMEDIATE test queries
            legacy_prepared_statements=False,
        )

        if session is None:
            connections[jwt_token] = new_connection
        else:
            # If a custom session is supplied, we can't reuse the same connection
            return new_connection

    return connections[jwt_token]


def __prepare_query(
    query: str, where_clause: str, limit: int | None, entries: list[list[str]] | list[str]
) -> tuple[str, list[str]]:
    """Prepare a bulk SQL query by expanding WHERE clause templates with multiple entries.

    This internal function constructs a parameterized SQL query by repeating a WHERE clause
    template for each entry in the list, combining them with OR operators. It validates that
    the number of parameters matches the placeholders in the where_clause.

    Args:
        query: Base SQL query (should end with or without WHERE keyword)
        where_clause: Template WHERE condition with ? placeholders for parameters
        limit: Optional LIMIT clause value to restrict result count
        entries: List of values or list of value lists to substitute into WHERE clause

    Returns:
        tuple: A tuple containing:
            - Final parameterized SQL query string (or "invalid" on error)
            - Flattened list of parameter values for query execution

    Example:
        query = "SELECT * FROM table"
        where_clause = "id = ?"
        entries = ["1", "2", "3"]
        Returns: ("SELECT * FROM table WHERE (id = ?) OR (id = ?) OR (id = ?)", ["1", "2", "3"])
    """
    # Count the number of parameter placeholders (?) in the WHERE clause template
    num_where_args = len([character for character in list(where_clause) if character == "?"])

    # Validate that the structure of entries matches the WHERE clause expectations
    if num_where_args == 1 and any(isinstance(entry, list) for entry in entries):
        logger.error(
            "Invalid number of arguments provided for where clause. The where clause has one "
            "?, but you provided a list of arguments."
        )
        return "invalid", []
    elif num_where_args > 1 and not all(isinstance(entry, list) for entry in entries):
        logger.error(
            "Invalid number of arguments provided for where clause. The where clause has %s "
            "?, but you did not provide a list of arguments.",
            num_where_args,
        )
        return "invalid", []
    elif num_where_args > 1 and not all(len(entry) == num_where_args for entry in entries):
        logger.error(
            "Invalid number of arguments provided for where clause. The where clause has %s "
            "?, but you provided a list of arguments of length %s.",
            num_where_args,
            len(entries[0]),
        )
        return "invalid", []

    # Build the final query by normalizing the base query and adding WHERE if needed
    final_query = query.strip()
    if not final_query.strip().lower().endswith("where"):
        final_query = final_query.strip() + " WHERE "
    else:
        final_query += " "

    # Build the OR-connected WHERE clauses and collect parameter values
    values = []
    for entry in entries:
        if not isinstance(entry, list):
            values.append(entry)
        else:
            values += entry

        final_query += f"({where_clause}) OR "

    # Remove the trailing " OR " from the last iteration
    final_query = final_query[:-4]

    if limit is not None:
        final_query += f" LIMIT {limit}"

    return final_query, values


def execute_bulk_query(
    cur: Cursor, query: str, where_clause: str, limit: int | None, entries: list[list[str]] | list[str]
) -> list[dict[str, Any]]:
    """Execute a bulk SQL query with multiple WHERE conditions combined with OR.

    This function constructs and executes a parameterized SQL query by expanding a WHERE
    clause template across multiple entries. Results are returned as dictionaries with
    column names as keys.

    Args:
        cur: Trino database cursor for query execution
        query: Base SQL query (with or without WHERE keyword)
        where_clause: Template WHERE condition with ? placeholders
        limit: Optional maximum number of results to return
        entries: List of parameter values or list of parameter value lists

    Returns:
        list[dict[str, Any]]: Query results as list of dictionaries, where each
            dictionary represents a row with column names as keys

    Example:
        execute_bulk_query(
            cur=cursor,
            query="SELECT * FROM users",
            where_clause="id = ?",
            limit=100,
            entries=["user1", "user2", "user3"]
        )
    """
    final_query, values = __prepare_query(query, where_clause, limit, entries)

    # Execute the prepared query with parameter values
    cur.execute(final_query, values)

    # Convert query results to list of dictionaries (column_name: value)
    results: list[dict[str, Any]] = []
    for row in cur.fetchall():
        results.append(dict(zip([desc.name for desc in cur.description], row)))

    return results
