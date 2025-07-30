import importlib
import inspect
import json
import os
import sys
import textwrap
from pathlib import Path
from typing import Callable
from urllib.parse import quote_plus

from flask.testing import FlaskClient
from termcolor import colored

from clue.plugin import CluePlugin

TESTABLE_FUNCTIONS = [
    ("get_actions", None),
    ("execute_action", "run_action"),
    ("get_fetchers", None),
    ("execute_fetcher", "run_fetcher"),
    ("get_type_names", None),
    ("lookup", "enrich"),
    ("bulk_lookup", "enrich"),
    ("liveness", None),
    ("readyness", None),
]


def success(*messages: str):
    "Print success message"
    print(f"[{colored("success", "green")}]", *messages)


def warn(*messages: str):
    "Print error message"
    print(f"[{colored("warn", "yellow")}]", *messages)


def error(*messages: str):
    "Print error message"
    print(f"[{colored("error", "red")}]", *messages)


def info(*messages: str):
    "Print info message"
    print(f"[{colored("info", "cyan")}]", *messages)


class CustomTestClient(FlaskClient):
    "Custom test client to inject authorization headers"

    def open(self, *args, buffered=False, follow_redirects=False, **kwargs):
        "Overriden open funciton to inject auth header"
        headers = kwargs.setdefault("headers", {})

        if "CLUE_ACCESS_TOKEN" in os.environ:
            info("Clue access token in env, setting Authorization header")
            headers["Authorization"] = f"Bearer {os.environ["CLUE_ACCESS_TOKEN"]}"
        else:
            warn("Missing access token, skipping authorization header.")

        return super().open(*args, buffered=buffered, follow_redirects=follow_redirects, **kwargs)


def filter_members(member, current_module):
    "Get a filtered list of members exported by a given application"
    member_module = inspect.getmodule(member)

    if member_module is None:
        return False

    if member_module == current_module:
        return True

    if not member_module.__name__.startswith("clue"):
        return False

    return True


def test_function(plugin: CluePlugin, fn_id: str, fn: Callable):  # noqa: C901
    "test a function"
    info(f"Executing test functionality for {fn_id}")

    plugin.app.test_client_class = CustomTestClient

    for rule in plugin.app.url_map.iter_rules():
        if rule.endpoint != fn_id:
            continue

        if "GET" in (rule.methods or {}) and "<" not in rule.rule:
            info("Simple endpoint detected. Running GET")
            response = plugin.app.test_client().get(rule.rule)
            info("Response:", json.dumps(response.json, indent=2) if response.json else response.data.decode())
        elif "GET" in (rule.methods or {}):
            kwargs: dict[str, str] = {}
            info(f"{len(rule.arguments)} arguments are necessary. Supply them now:")
            for argument in sorted(list(rule.arguments)):
                kwargs[argument] = quote_plus(quote_plus(input(f"{argument}: ")))

            with plugin.app.test_request_context():
                path = plugin.app.url_for(fn_id, **kwargs)  # type: ignore[arg-type]
                info(f"Making request to path {path}")

                response = plugin.app.test_client().get(path)

                if response.status_code > 299:
                    error(
                        (response.json or {}).get(
                            "api_error_message", f"An unknown error occurred. Full response:\n{response.text}"
                        )
                    )
                else:
                    info("Response:", json.dumps(response.json, indent=2) if response.json else response.data.decode())
        elif "POST" in (rule.methods or {}):
            kwargs: dict[str, str] = {}
            if "<" in rule.rule:
                info(f"{len(rule.arguments)} arguments are necessary. Supply them now:")
                for argument in sorted(list(rule.arguments)):
                    kwargs[argument] = quote_plus(quote_plus(input(f"{argument}: ")))

            info(
                "Endpoint requires POST data. You can probide a JSON file for this data. "
                f"Provide a path relative to {os.getcwd()} or an absolute path."
            )
            json_path = Path(os.getcwd()) / input("Path to JSON: ").strip()

            if not json_path.exists() or json_path.is_dir():
                error(f"Provided path {json_path} is invalid or is a directory.")
                return

            with json_path.open("r") as _data, plugin.app.test_request_context():
                try:
                    post_data = json.load(_data)
                except json.JSONDecodeError:
                    error(f"The file data in {json_path} is not valid JSON.")
                    return

                api_path = rule.rule if "<" not in rule.rule else plugin.app.url_for(fn_id, **kwargs)  # type: ignore[arg-type]

                info(f"Submitting POST request to {api_path}:\n{post_data}")

                response = plugin.app.test_client().post(
                    api_path,
                    data=json.dumps(post_data),
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code > 299:
                    error(
                        (response.json or {}).get(
                            "api_error_message", f"An unknown error occurred. Full response:\n{response.text}"
                        )
                    )
                else:
                    info("Response:", json.dumps(response.json, indent=2) if response.json else response.data.decode())


def main():  # noqa: C901
    "main interactive loop"
    os.environ["ENABLE_CACHE"] = "false"

    plugin_name = None
    if len(sys.argv) > 1:
        plugin_name = sys.argv[1]

        if not (Path(__file__).parent.parent.parent / "plugins" / plugin_name).exists():
            error(f"Plugin {plugin_name} does not exist.")
            plugin_name = None

    while plugin_name is None:
        plugin_name = input("What plugin do you want to interact with?\n> ")
        if not (Path(__file__).parent.parent.parent / "plugins" / plugin_name).exists():
            error(f"Plugin {plugin_name} does not exist.")
            plugin_name = None

    try:
        _module = importlib.import_module(f"plugins.{plugin_name}.app")
        success(f"Initializing plugin {plugin_name} for interactivity")
    except Exception:
        error(f"Initializing plugin {plugin_name} for interactivity")
        raise

    plugin: CluePlugin | None = None
    for key, member in inspect.getmembers(_module, predicate=lambda _m: filter_members(_m, _module)):
        if isinstance(member, CluePlugin):
            success(f"Plugin found exported as member {key}")
            plugin = member
            break

    if plugin is None:
        error("CluePlugin object is not exported from this module!")
        return

    plugin.cache = None

    functions: list[tuple[str, Callable]] = []

    for attribute in dir(plugin):
        test_entry = next((entry for entry in TESTABLE_FUNCTIONS if entry[0] == attribute), None)
        if test_entry is None:
            continue

        fn = plugin.__getattribute__(attribute)
        if fn is None:
            continue

        if test_entry[1] is not None:
            helper_fn = plugin.__getattribute__(test_entry[1])

            if helper_fn is None:
                continue

        functions.append((attribute, fn))

    choice: int | None = None

    print(
        textwrap.dedent("""
        Clue Plugin Development Script

        This script will help you test various aspects of your plugin interactively.
        """),
    )

    if "CLUE_ACCESS_TOKEN" not in os.environ:
        warn(
            textwrap.dedent("""
            Environment variable CLUE_ACCESS_TOKEN not set!

            It is highly likely your plugin will not work if it connects to an external service.
            """).strip()  # noqa: E501
        )

    while choice is None:
        print("\nAvailable functions:")

        for i in range(len(functions)):
            print(f"{i + 1}) {' '.join(word.capitalize() for word in functions[i][0].split("_"))}")
        print(f"{len(functions) + 1}) Quit")

        action = input("\nEnter a selection: ")

        try:
            choice = int(action)

            if choice > len(functions) + 1:
                error(f"Invalid choice, choose option between 1 - {len(functions)}.")
                choice = None
        except ValueError:
            error(f"Invalid integer, choose option between 1 - {len(functions)}.")

        if choice is not None and choice <= len(functions):
            test_function(plugin, *functions[choice - 1])
            choice = None


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\rExiting!" + " " * 80)
