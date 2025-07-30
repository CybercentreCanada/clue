import ast
import re
import warnings
from pathlib import Path

from test.conftest import get_api_data


# noinspection PyUnusedLocal
def test_doc(login_session):
    session, host = login_session

    api_list = get_api_data(session, f"{host}/api/")
    assert len(api_list) > 0

    for api in api_list:
        resp = get_api_data(session, f"{host}/api/{api}/")
        assert "apis" in resp and "blueprints" in resp


def test_plugin_formatting(login_session):
    session, host = login_session

    file_path = Path.cwd() / "plugins"

    if not file_path.exists():
        return

    for plugin in file_path.iterdir():
        plugin_file = Path.cwd() / "plugins" / plugin.name / "app.py"

        if plugin_file is None:
            raise FileNotFoundError("The docstring for this plugin does not exist!")

        try:
            with open(plugin_file, "r", encoding="utf-8") as file:
                # Read the file contents
                contents = file.read()

            parsed = ast.parse(contents)

            file_docstring = ast.get_docstring(parsed)

            assert file_docstring is not None, f"The {plugin.name} plugin is missing its docstring!"

            assert (
                "Point of Contact:" in file_docstring
            ), f"The {plugin.name} plugin is missing a Point of Contact for the plugin"

            assert "Team:" in file_docstring, f"The {plugin.name} plugin is missing the Team for the plugin"

            assert (
                "Status: Production" in file_docstring
                or "Status: In Development"
                or "Status: No Active Development" in file_docstring
            ), f"The {plugin.name} plugin is missing the status of the plugin"

        except FileNotFoundError:
            pass


def test_formatting(login_session):
    session, host = login_session

    api_list = get_api_data(session, f"{host}/api/")

    for api in api_list:
        resp = get_api_data(session, f"{host}/api/{api}/")

        for api in resp["apis"]:
            description: str = api["description"]
            assert len(description) > 0, f"Endpoint {api['function']} is missing its docstring!"

            path: str = api["path"]
            matches = re.findall(r"<(\w+)>", path)

            assert re.search(
                r"\n *Variables:", description
            ), f"Endpoint {api['function']} is missing a Variables: portion of the docstring!"

            if len(matches) > 0:
                desc_parts = [
                    line
                    for line in description.splitlines()
                    if line.startswith("Variables:") or any(line.startswith(match) for match in matches)
                ]

                variables_err = (
                    f"Endpoint {api['function']} is missing a properly formatted Variables: portion of "
                    "the docstring!"
                )

                if len(desc_parts) != len(matches) + 1:
                    warnings.warn(variables_err)
                elif any("=>" not in line for line in desc_parts[1:]):
                    warnings.warn(variables_err)

            assert re.search(r"\n *Arguments:", description) or re.search(
                r"\n *Optional Arguments:", description
            ), f"Endpoint {api['function']} is missing an Arguments: portion of the docstring!"

            if (
                "POST" not in api["methods"]
                and "PUT" not in api["methods"]
                and "PATCH" not in api["methods"]
                and "DELETE" not in api["methods"]
            ):
                assert not re.search(r"Data Block:", description), (
                    f"Endpoint {api['function']} has a Data Block: portion despite not permitting PATCH, POST or "
                    "PUT methods!"
                )
            elif "POST" in api["methods"] or "PUT" in api["methods"] or "PATCH" in api["methods"]:
                assert re.search(r"Data Block:", description), (
                    f"Endpoint {api['function']} doesn't have a Data Block: portion despite permitting PATCH, POST or "
                    "PUT methods!"
                )

            assert re.search(
                r"\n *Result Example:", description
            ), f"Endpoint {api['function']} doesn't have a Result Example: portion!"

            headers = [line.strip() for line in description.splitlines() if line.endswith(":")]

            header_error = (
                f"Endpoint {api['function']} has headers in the incorrect order! Header order should be: "
                "Variables, Arguments, Optional Arguments, Data Block, Result Example"
            )

            assert headers[0] == "Variables:", header_error
            assert headers[1].endswith("Arguments:"), header_error
            assert headers[-1] == "Result Example:", header_error

            if "Arguments:" in headers and "Optional Arguments:" in headers:
                assert headers[1] == "Arguments:" and headers[2] == "Optional Arguments:", header_error

            if "Data Block:" in headers:
                assert headers[-2] == "Data Block:", header_error
