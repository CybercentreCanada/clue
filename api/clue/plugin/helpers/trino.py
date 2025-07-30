import os
from typing import Any, Literal, cast

from flask import request
from trino.auth import JWTAuthentication
from trino.dbapi import Connection, Cursor, connect

from clue.common.logging import get_logger
from clue.plugin.helpers.token import get_username

logger = get_logger(__file__)


def get_trino_connection(
    app_name: str,
    connections: dict[str, Connection],
    classification: Literal["u"] | Literal["pb"] = "pb",
    request_timeout: int = 60,
    max_attempts: int = 2,
    username_claims: list[str] | None = None,
    access_token: str | None = None,
) -> Connection:
    "Get a trino connection based on the provided JWT"
    jwt_token: str = access_token or cast(str, request.headers.get("Authorization", None, type=str)).split(" ")[1]
    if jwt_token not in connections:
        connections[jwt_token] = connect(
            http_scheme="https",
            host=os.environ.get("TRINO_HOST", f"trino.hogwarts.{classification}.azure.chimera.cyber.gc.ca"),
            port=int(os.environ.get("TRINO_PORT", "443")),
            user=get_username(jwt_token, claims=username_claims),
            auth=JWTAuthentication(jwt_token),
            source=f"clue-{app_name}",
            max_attempts=max_attempts,
            request_timeout=request_timeout,
            # This will stop trino from being bombarded with EXECUTE IMMEDIATE test queries
            legacy_prepared_statements=False,
        )

    return connections[jwt_token]


def __prepare_query(
    query: str, where_clause: str, limit: int | None, entries: list[list[str]] | list[str]
) -> tuple[str, list[str]]:
    num_where_args = len([character for character in list(where_clause) if character == "?"])
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

    final_query = query.strip()
    if not final_query.strip().lower().endswith("where"):
        final_query = final_query.strip() + " WHERE "
    else:
        final_query += " "

    values = []
    for entry in entries:
        if not isinstance(entry, list):
            values.append(entry)
        else:
            values += entry

        final_query += f"({where_clause}) OR "

    final_query = final_query[:-4]

    if limit is not None:
        final_query += f" LIMIT {limit}"

    return final_query, values


def execute_bulk_query(
    cur: Cursor, query: str, where_clause: str, limit: int | None, entries: list[list[str]] | list[str]
) -> list[dict[str, Any]]:
    "Build a bulk SQL query based on a main query, a template where clause, and a list of entries."
    final_query, values = __prepare_query(query, where_clause, limit, entries)

    cur.execute(final_query, values)

    results: list[dict[str, Any]] = []
    for row in cur.fetchall():
        results.append(dict(zip([desc.name for desc in cur.description], row)))

    return cur.fetchall()
