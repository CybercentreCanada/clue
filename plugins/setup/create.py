import sys
from pathlib import Path

PLUGINS_FOLDER = Path(__file__).parent.parent.resolve()
CLUE_PATH = Path(__file__).parent.parent.parent / "api"
CLUE_VENV_PATH = CLUE_PATH / ".venv/lib/python3.12/site-packages"
sys.path.append(str(CLUE_PATH))
sys.path.append(str(CLUE_VENV_PATH))

import re
import shutil
from email.utils import parseaddr

import yaml
from click.termui import confirm
from clue.constants.supported_types import SUPPORTED_TYPES
from commands import error, execute, header, info, prep_command, success, wait_to_continue

TEMPLATES_FOLDER = Path(__file__).parent / "templates"


def get_plugin_name() -> str:
    """Prompt user for a valid plugin name.

    Continuously prompts the user until a valid plugin name is provided.
    A valid name must contain only lowercase letters, numbers, and hyphens,
    and must not already exist in the plugins folder.

    Returns:
        str: The validated plugin name.
    """
    plugin_name: str | None = None
    while plugin_name is None:
        candidate = input("\nPlugin Name: ").lower()

        if not candidate:
            continue

        if re.sub(r"[a-z0-9\-]", "", candidate):
            error("Plugin name can only contain lowercase letters, numbers, and hyphens.")
            continue

        if (PLUGINS_FOLDER / candidate.replace("-", "_")).exists():
            error(
                f"Plugin {candidate} already exists at {PLUGINS_FOLDER / candidate.replace('-', '_')} - please use a "
                "different name."
            )
            continue

        plugin_name = candidate

    return plugin_name


def get_team() -> str:
    """Prompt user for the team that owns the plugin.

    Continuously prompts the user until a non-empty team name is provided.

    Returns:
        str: The team name that owns the plugin.
    """
    team: str | None = None
    while team is None:
        team = input("\nTeam Ownership (what team/organization owns this plugin?): ")

        if not team:
            error("You must specify a team.")
            team = None
            continue

    return team


def get_contact() -> str:
    """Prompt user for a point of contact in RFC-5322 format.

    Continuously prompts the user until a valid contact is provided in the format
    'Full Name <email@example.com>'. Both name and email components are required.

    Returns:
        str: The validated contact information in RFC-5322 format.
    """
    contact: str | None = None
    while contact is None:
        contact = input("\nPoint of Contact (format should be 'Full Name <email address>'): ")

        if not contact:
            error("You must specify a point of contact.")
            contact = None
            continue

        name, email = parseaddr(contact)
        if not name or not email:
            error("You must specify the point of contact in RFC-5322 address format.")
            contact = None
            continue

    return contact


def main():
    """Interactive wizard to create a new Clue plugin.

    Guides the user through the plugin creation process by:
    - Prompting for plugin name, team ownership, and contact information
    - Creating the plugin directory structure
    - Generating README.md, manifest.yml, and optional app.py files
    - Optionally creating stub enrich and action functions
    - Optionally creating a GitHub Actions workflow file
    - Running code formatting and linting on generated files

    Raises:
        KeyboardInterrupt: If the user cancels the operation with Ctrl+C.
    """
    try:
        header("Clue Plugin Generation", "This script will walk you through the creation of a new clue plugin.")

        wait_to_continue()

        info("First, we need a name for your plugin. It must not match an existing plugin name.")

        existing_plugins = sorted(
            entry.name.replace("_", "-")
            for entry in PLUGINS_FOLDER.iterdir()
            if entry.is_dir()
            and not re.sub(r"[a-z0-9_]", "", entry.name, flags=re.IGNORECASE)
            and not entry.name.startswith("_")
        )

        info(f"Existing plugins are: {', '.join(existing_plugins)}")

        plugin_name = get_plugin_name()
        plugin_name_pretty = " ".join(word.capitalize() for word in plugin_name.split("-"))

        info("Provide a small amount of information for the README file.")

        team = get_team()

        contact = get_contact()

        description = "No description provided."
        if confirm("Would you like to provide a short (one line) description?", default=True):
            description = input("\nPlugin Description: ")

        plugin_path = PLUGINS_FOLDER / plugin_name.replace("-", "_")
        info(f"Creating directory {plugin_path} (permissions inherited from parent folder)")
        plugin_path.mkdir(mode=PLUGINS_FOLDER.stat().st_mode)

        md_template = (TEMPLATES_FOLDER / "README.md").read_text()

        info("Creating README.md")
        (plugin_path / "README.md").write_text(
            md_template.replace("$PLUGIN_TITLE", " ".join(word.capitalize() for word in plugin_name.split("-")))
            .replace("$TEAM", team)
            .replace("$CONTACT", contact)
            .replace("$DESCRIPTION", description)
        )

        info("Creating .dockerignore")
        shutil.copy(TEMPLATES_FOLDER / ".dockerignore", plugin_path)

        manifest_template = (TEMPLATES_FOLDER / "manifest.yml").read_text()

        info("Creating manifest.yml")
        (plugin_path / "manifest.yml").write_text(manifest_template.replace("$PLUGIN_NAME", plugin_name))

        if confirm("Add stub app.py file?", default=True):
            app_py_content = (
                (TEMPLATES_FOLDER / "app.py")
                .read_text()
                .replace("$PLUGIN_NAME", plugin_name)
                .replace("$PLUGIN_TITLE", plugin_name_pretty)
                .replace("$TEAM", team)
                .replace("$CONTACT", contact)
                .replace("$DESCRIPTION", description)
            )

            imports, body = app_py_content.split("\n# ---\n", maxsplit=1)

            types: set[str] = set()
            if confirm("Add stub enrich function?", default=True):
                print()
                info("You will need to provide a list of supported types. Default types supported by clue are:")
                info(", ".join(SUPPORTED_TYPES))
                info("Once you have added all the types, jsut press enter to continue.")

                new_type = input(f"supported types: [{','.join(types)}] > ")

                while new_type:
                    types.add(new_type)
                    new_type = input(f"supported types: [{','.join(types)}] > ")

                enrich_function_imports, enrich_function_body = (
                    (TEMPLATES_FOLDER / "enrich_function.py").read_text().split("\n# ---\n", maxsplit=1)
                )

                imports = imports + enrich_function_imports
                body = body + enrich_function_body

            if confirm("Add stub action function?", default=False):
                print()

                action_functions_imports, action_functions_body = (
                    (TEMPLATES_FOLDER / "action_functions.py").read_text().split("\n# ---\n", maxsplit=1)
                )

                imports = imports + action_functions_imports
                body = body + action_functions_body

            body = body.replace("$SUPPORTED_TYPES", ",".join(sorted(list(types))))

            finished_app_py = re.sub(r" *# type: ignore *# noqa: F821", "", imports + "\n" + body)

            (plugin_path / "app.py").write_text(finished_app_py)

            execute(
                prep_command(f"ruff format {plugin_name.replace('-', '_')}"), cwd=PLUGINS_FOLDER, capture_output=True
            )
            execute(
                prep_command(f"ruff check --fix {plugin_name.replace('-', '_')}"),
                cwd=PLUGINS_FOLDER,
                capture_output=True,
            )

        if confirm("Add new workflow for your plugin?", default=True):
            workflow_content = (
                (TEMPLATES_FOLDER / "template-workflow.yml")
                .read_text()
                .replace("$PLUGIN_NAME_CAPITALIZED", plugin_name_pretty)
                .replace("$PLUGIN_NAME", plugin_name.replace("-", "_"))
            )

            (PLUGINS_FOLDER.parent / ".github" / "workflows" / f"{plugin_name}-plugin-workflow.yml").write_text(
                workflow_content
            )

        if confirm("Add helm chart?", default=True):
            info("creating Chart.yaml and values files")
            helm_path = plugin_path / "helm"
            helm_path.mkdir(exist_ok=True, parents=True)

            chart_yaml_content = (
                (TEMPLATES_FOLDER / "helm" / "Chart.yaml")
                .read_text()
                .replace("$PLUGIN_NAME", plugin_name.replace("_", "-"))
            )

            (helm_path / "Chart.yaml").write_text(chart_yaml_content)

            helm_values_path = helm_path / "values"
            helm_values_path.mkdir(exist_ok=True, parents=True)

            values_yaml_content = (
                (TEMPLATES_FOLDER / "helm" / "values" / "values.PLUGIN_NAME.yaml")
                .read_text()
                .replace("$PLUGIN_NAME", plugin_name.replace("_", "-"))
            )

            values_yaml_path = helm_values_path / f"values.{plugin_name.replace('-', '_')}.yaml"
            values_yaml_path.write_text(values_yaml_content)

            info("adding chart to helmfile.yaml")
            helmfile_path = PLUGINS_FOLDER / "helmfile.yaml"
            with helmfile_path.open("r") as f:
                helmfile_data = yaml.safe_load(f)
            helmfile_data["releases"].append(
                {
                    "chart": helm_path.relative_to(helmfile_path.parent).as_posix(),
                    "name": plugin_name.replace("_", "-"),
                    "namespace": "clue-plugins",
                    "values": [values_yaml_path.relative_to(helmfile_path.parent).as_posix()],
                }
            )
            with helmfile_path.open("w") as f:
                yaml.safe_dump(helmfile_data, f)

        success("Your plugin has been created!")
    except KeyboardInterrupt:
        print()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\rExiting!" + " " * 80)
