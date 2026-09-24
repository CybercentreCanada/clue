from typing import Any


def register_prompts(mcp: Any) -> None:
    """Register reusable instructions for Clue MCP workflows."""

    @mcp.prompt(name="get_actions")
    def get_actions_prompt() -> str:
        return """Use the get_actions tool to list the external actions available to the current user.

Return the action keys and summarize each action's purpose, supported types, classification,
whether it accepts multiple or empty inputs, whether it is asynchronous, and its parameter schema.
Do not invent actions or parameters that are absent from the tool response.
"""

    @mcp.prompt(name="execute_action")
    def get_execute_action_prompt() -> str:
        return """Execute a Clue external action.

1. Use get_actions and select an exact `<plugin_id>.<action_id>` key.
2. Check supported_types, accept_multiple, accept_empty, classification, and params.
3. Call execute_action with plugin_id and action_id. Supply selector for one value or selectors for
    multiple values, context when relevant, and plugin-specific top-level fields in parameters.
4. If the result outcome is pending and includes task_id, call get_action_status with the same
   plugin_id and action_id until the result is no longer pending. Do not fabricate a task ID.
5. Report the final outcome, summary, format, and output without changing their meaning.
"""

    @mcp.prompt(name="get_action_status")
    def get_action_status_prompt() -> str:
        return """Use get_action_status to retrieve a previously started asynchronous action.

Provide the original plugin_id and action_id and the task_id returned by execute_action. If the
outcome remains pending, preserve the task ID for a later status check. Otherwise report the final
outcome, summary, format, and output.
"""

    @mcp.prompt(name="get_fetchers")
    def get_fetchers_prompt() -> str:
        return """Use the get_fetchers tool to list fetchers available to the current user.

Return the fetcher keys and summarize each fetcher's description, supported types, classification,
output format, and whether it is asynchronous. Do not invent fetchers absent from the response.
"""

    @mcp.prompt(name="run_fetcher")
    def get_run_fetcher_prompt() -> str:
        return """Run a Clue fetcher for one typed value.

1. Use get_fetchers and select an exact `<plugin_id>.<fetcher_id>` key compatible with the value's
   type and classification.
2. Call run_fetcher with plugin_id, fetcher_id, and a selector containing type and value. Include
   classification or sources only when known. Optionally set max_timeout in seconds.
3. If the result outcome is pending and includes task_id, call get_fetcher_status with the same IDs.
4. Report returned data, link, format, error, and outcome without inventing missing fields.
"""

    @mcp.prompt(name="get_fetcher_status")
    def get_fetcher_status_prompt() -> str:
        return """Use get_fetcher_status to retrieve a previously started asynchronous fetcher.

Provide the original plugin_id and fetcher_id and the task_id returned by run_fetcher. If the
outcome remains pending, preserve the task ID for a later status check; otherwise report the final
result and any error.
"""

    @mcp.prompt(name="get_types")
    def get_types_prompt() -> str:
        return """Use get_types to list data types supported by each configured external source.

Group the response by source and reproduce type names exactly so they can be passed to enrich,
bulk_enrich, actions, or fetchers.
"""

    @mcp.prompt(name="get_types_detection")
    def get_types_detection_prompt() -> str:
        return """Use get_types_detection to retrieve Clue's regular expressions for detecting data types.

Return each type with its exact pattern. Treat the expressions as detection hints; do not execute
untrusted input as code or claim that a pattern guarantees a value is safe.
"""

    @mcp.prompt(name="bulk_enrich")
    def get_bulk_enrich_prompt() -> str:
        return """Enrich multiple values with Clue.

Call bulk_enrich with a non-empty data list. Each selector needs type and value and may include
classification and sources. Use options for global filtering, timeouts, cache behavior, or output
detail. Preserve result grouping and clearly distinguish source errors from empty results.
"""

    @mcp.prompt(name="enrich")
    def get_enrich_prompt() -> str:
        return """Enrich one value with Clue.

Call enrich with the exact type_name and the raw, unencoded value; the tool handles URL encoding.
Use options for source filtering, timeouts, cache behavior, or output detail. Summarize results by
source and preserve links, counts, classifications, annotations, raw values, and source errors.
"""

    @mcp.prompt(name="serve_documentation")
    def get_serve_documentation_prompt() -> str:
        return """Use serve_documentation to retrieve available Clue Markdown documentation.

Optionally provide documentation_filter to match filenames. Summarize the relevant documents and
name their source files. An empty response means no filenames matched the filter.
"""

    @mcp.prompt(name="serve_documentation_file")
    def get_serve_documentation_file_prompt() -> str:
        return """Use serve_documentation_file to retrieve one Clue Markdown document.

Pass a relative filename or nested documentation path including its extension. Summarize only the
returned document and retain important commands, configuration names, and warnings exactly.
"""
