# Clue MCP Server Release Notes

## `v0.1.0`

- **Clue MCP Server** *(new feature)*: Added a FastMCP server exposing authenticated enrichment, action, fetcher, type-discovery, and documentation tools, with guidance prompts ([#92](https://github.com/CybercentreCanada/clue/pull/92)).
- **Token Pass-Through** *(new feature)*: Validates the caller's JWT signature and claims using Keycloak JWKS, then forwards the same user token to the Clue API. The API remains responsible for authorization.
- **Deployment** *(new feature)*: Added a container image, environment-based configuration, and local development setup. See the [MCP README](https://github.com/CybercentreCanada/clue/blob/main/mcp/README.md) for configuration, testing, and deployment details.
