# Clue MCP Server

## Overview

Clue MCP is a FastMCP server that exposes authenticated Clue enrichment, external action,
fetcher, lookup, and documentation tools.

Request flow:

1. The MCP runtime provides the caller bearer token.
2. The server validates token signature and claims using Keycloak JWKS.
3. The same user token is forwarded to the Clue API.
4. The tool returns the Clue API result.

This service intentionally uses token pass-through. It does not mint a second backend token.

## Current Tool Surface

The server currently registers these tools:

| Tool                     | Backend path                               | Method | Purpose                                                       |
| ------------------------ | ------------------------------------------ | ------ | ------------------------------------------------------------- |
| get_actions              | /actions/                                  | GET    | List external actions available to the current user.          |
| execute_action           | /actions/execute/{plugin}/{action}        | POST   | Execute a configured external action.                         |
| get_action_status        | /actions/{plugin}/{action}/status/{task}   | GET    | Retrieve the status of an asynchronous action.                 |
| get_fetchers             | /fetchers/                                 | GET    | List external fetchers available to the current user.         |
| run_fetcher              | /fetchers/{plugin}/{fetcher}               | POST   | Run a fetcher for one typed value.                            |
| get_fetcher_status       | /fetchers/{plugin}/{fetcher}/status/{task} | GET    | Retrieve the status of an asynchronous fetcher.               |
| get_types                | /lookup/types/                             | GET    | List types supported by each external source.                |
| get_types_detection      | /lookup/types_detection/                  | GET    | Return regular expressions for detecting data types.          |
| enrich                   | /lookup/enrich/{type}/{value}/             | GET    | Enrich one typed value through external sources.             |
| bulk_enrich              | /lookup/enrich                            | POST   | Enrich multiple typed values through external sources.        |
| serve_documentation      | /static/docs                              | GET    | Return available Clue Markdown documentation.                 |
| serve_documentation_file | /static/docs/{filename}                   | GET    | Return one Clue Markdown documentation file.                  |

Action and fetcher identifiers use the exact `<plugin_id>.<action_id>` and
`<plugin_id>.<fetcher_id>` keys returned by their discovery tools. The available actions, fetchers,
types, and documentation depend on the configured Clue API and the authenticated user's access.

## Prompt Surface

The server currently registers prompt guidance for:

- get_actions
- execute_action
- get_action_status
- get_fetchers
- run_fetcher
- get_fetcher_status
- get_types
- get_types_detection
- enrich
- bulk_enrich
- serve_documentation
- serve_documentation_file

## Capability Summary

Current server capabilities:

- Authenticates requests by validating JWT signature and claims via Keycloak JWKS.
- Forwards the validated user token to the Clue API (token pass-through model).
- Exposes discovery tools for external actions, fetchers, supported data types, and type detection patterns.
- Supports single-value and bulk enrichment with source, classification, timeout, cache, and output controls.
- Supports synchronous and asynchronous external actions and fetchers, including status lookup.
- Serves Clue Markdown documentation through filtered listing and individual file retrieval.

## Project Layout

- clue_mcp/server.py: FastMCP server construction and lifecycle.
- clue_mcp/auth.py: JWT verifier and token pass-through provider.
- clue_mcp/api.py: HTTP client wrapper for the Clue API.
- clue_mcp/tools.py: MCP tool registration, route validation, and enrichment option handling.
- clue_mcp/prompts.py: Prompt registration.
- clue_mcp/config.py: Environment-driven config with HTTPS enforcement for non-local hosts.
- dev/dev_setup.py: local developer bootstrap helper.

## Development Helper (dev_setup)

The dev helper script exists for local development with the dockerized test realm:

- Writes mcp/.env with the local client secret when available.
- Optionally verifies Keycloak reachability.
- Optionally fetches a local dev bearer token.
- Optionally writes .vscode/mcp.json Authorization header for instant local MCP usage.

By default, `--start` only manages the MCP server itself (clears its port, verifies Keycloak,
fetches a token, updates `.vscode/mcp.json`, and runs the server). Dependencies
(MongoDB/Redis/Keycloak/Clue API) are assumed to already be running; start them
separately with `docker compose up -d` (from api/dev/) if needed.

This local token write is intentional for developer productivity in local docker environments. Non-development environments are expected to use proper secret handling and environment-specific auth setup managed by the operator.

Security note: `mcp/.env` and `.vscode/mcp.json` are gitignored and chmod'd to 0600 by the
script right after writing, since neither VS Code's `http` server transport (`headers`/`oauth`
only, no `env`/`envFile`) nor `docker compose` support pulling these values from an environment
variable at that point — a literal dev-only secret is unavoidable for zero-prompt automation.
Static analysis findings about clear-text secret storage on these lines are expected and
mitigated by file permissions rather than suppressed by design changes.

Typical usage from mcp/:

- poetry run python -m dev.dev_setup
- poetry run python -m dev.dev_setup --verify
- poetry run python -m dev.dev_setup --token
- poetry run python -m dev.dev_setup --start

## Environment Variables

Primary runtime variables:

- CLUE_API_BASE_URL (defaults to `http://localhost:5000/api/v1`)
- CLUE_API_HOST
- CLUE_API_PORT
- CLUE_API_TIMEOUT
- CLUE_API_MAX_CONNECTIONS
- CLUE_API_MAX_KEEPALIVE_CONNECTIONS
- CLUE_API_KEEPALIVE_EXPIRY
- AUTH_ISSUER
- AUTH_JWKS_URI
- AUTH_TOKEN_URL
- AUTH_CLIENT_ID
- AUTH_CLIENT_SECRET (optional in local public-client flow, often required in managed deployments)
- MCP_BASE_URL
- MCP_HOST
- MCP_PORT
- MCP_LOG_LEVEL
- MCP_AUDIENCE
- MCP_SCOPE

Config guardrails:

- config.py allows http for local hosts and configured Docker/Kubernetes service names.
- non-local endpoints must use https.
- config.py calls `load_dotenv()`, so a `mcp/.env` file is
  picked up automatically on import; vars already exported in the shell take precedence.

## Local Run

From mcp/:

1. poetry install
2. poetry run python -m clue_mcp.server

Why module execution is used:

- package-relative imports require module execution from the MCP project root.

## Tests

Unit tests (mocked API, no network):

- poetry run pytest test/test_tools.py -v
- poetry run pytest test/test_api.py -v
- poetry run pytest test/test_dev_setup.py -v

Optional live network tests:

1. export RUN_MCP_NETWORK_TESTS=1
2. export TEST_AUTH_USERNAME=<username>
3. export TEST_AUTH_PASSWORD=<password>
4. export TEST_AUTH_EMAIL=<email>
5. poetry run pytest test/test_network.py -v

## Linting and Validation

Run Ruff linting and formatting from `mcp/`:

- `poetry run ruff check .`
- `poetry run ruff format .`

## Deployment Notes

Container:

- docker build --secret id=pip_ca,src=${PIP_CERT:-/etc/ssl/certs/ca-certificates.crt} -t clue-mcp-server:latest .
- docker compose --profile full up -d

Repository compose currently uses an explicit bridge network for communication between services. For production, also apply ingress and egress policy controls appropriate to the deployment environment.

The shared Clue API HTTP client is created when the streamable-HTTP application starts, using the configured connection limits, and is closed when the application shuts down.

Kubernetes recommendations:

- inject secrets via Kubernetes Secret.
- restrict ingress and egress paths.
- add readiness and liveness probes.
- monitor token verification failures and backend authorization failures.

## Common Failures

401 or 403 from MCP:

- token missing MCP_SCOPE.
- token audience missing MCP_AUDIENCE.
- issuer or JWKS mismatch.

401 or 403 from Clue API:

- forwarded user token is not accepted by Clue API policies.

Empty or failed tool execution:

- no external actions, fetchers, or types are configured for the authenticated user.
- the requested plugin, action, or fetcher is not available to the authenticated user.
- use `get_actions`, `get_fetchers`, and `get_types` before calling configured external services.
- an empty enrichment result can be valid when no source returns data for the supplied value.

## Security Model Summary

- Authentication and authorization are enforced by JWT verification and downstream API controls.
- Tool-level validation focuses on request correctness and usability.
- API-side validation remains authoritative for enforcement.
