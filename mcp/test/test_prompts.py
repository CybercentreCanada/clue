from collections.abc import Callable

from clue_mcp.prompts import register_prompts


class _CaptureMCP:
    def __init__(self):
        self.prompts: dict[str, Callable[[], str]] = {}

    def prompt(self, name: str):
        def decorator(prompt):
            self.prompts[name] = prompt
            return prompt

        return decorator


def test_register_prompts_registers_and_returns_guidance():
    mcp = _CaptureMCP()
    register_prompts(mcp)

    expected_opening = {
        "get_actions": "Use the get_actions tool",
        "execute_action": "Execute a Clue external action.",
        "get_action_status": "Use get_action_status",
        "get_fetchers": "Use the get_fetchers tool",
        "run_fetcher": "Run a Clue fetcher",
        "get_fetcher_status": "Use get_fetcher_status",
        "get_types": "Use get_types",
        "get_types_detection": "Use get_types_detection",
        "bulk_enrich": "Enrich multiple values with Clue.",
        "enrich": "Enrich one value with Clue.",
        "serve_documentation": "Use serve_documentation",
        "serve_documentation_file": "Use serve_documentation_file",
    }

    assert set(mcp.prompts) == set(expected_opening)
    for name, opening in expected_opening.items():
        assert mcp.prompts[name]().startswith(opening)
