import re
import shutil
import sys
from email.utils import parseaddr
from pathlib import Path

from click.termui import confirm

from clue.constants.supported_types import SUPPORTED_TYPES
from plugin.commands import (
    error,
    execute,
    header,
    info,
    prep_command,
    success,
    wait_to_continue,
)

PLUGINS_FOLDER: Path = (Path(__file__).parent.parent.parent / "plugins").resolve()
TEMPLATES_FOLDER = Path(__file__).parent / "templates"


def get_plugin_name() -> str:
    plugin_name: str | None = None
    while plugin_name is None:
        candidate = input("\nPlugin Name: ").lower()

        if not candidate:
            continue

        if re.sub(r"[a-z0-9\-]", "", candidate):
            error("Plugin name can only contain lowercase letters, numbers, and hyphens.")
            continue

        if (PLUGINS_FOLDER / candidate).exists():
            error(f"Plugin {candidate} already exists at {PLUGINS_FOLDER / candidate} - please use a different name.")
            continue

        plugin_name = candidate

    return plugin_name


def get_team() -> str:
    team: str | None = None
    while team is None:
        team = input("\nTeam Ownership (what team/organization owns this plugin?): ")

        if not team:
            error("You must specify a team.")
            team = None
            continue

    return team


def get_contact() -> str:
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
    try:
        header("Clue Plugin Generation", "This script will walk you through the creation of a new clue plugin.")

        wait_to_continue()

        info("First, we need a name for your plugin. It must not match an existing plugin name.")

        existing_plugins = sorted(
            entry.name
            for entry in PLUGINS_FOLDER.iterdir()
            if entry.is_dir() and not re.sub(r"[a-z0-9\-]", "", entry.name, flags=re.IGNORECASE)
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

        success("Your plugin has been created!")
    except KeyboardInterrupt:
        print()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\rExiting!" + " " * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\rExiting!" + " " * 80)
