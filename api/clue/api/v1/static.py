import os
from pathlib import Path

from flask import request
from flask_cors import CORS

from clue.api import make_subapi_blueprint, not_found, ok
from clue.common.logging import get_logger
from clue.common.swagger import generate_swagger_docs
from clue.config import config
from clue.security import api_login
from clue.security.utils import is_path_traversal

SUB_API = "static"
static_api = make_subapi_blueprint(SUB_API, api_version=1)
static_api._doc = "Fetch static documentation"

CORS(static_api, origins=config.ui.cors_origins, supports_credentials=True)

DOCUMENTATION_FOLDER = (
    Path(os.environ.get("CLUE_DOCUMENTATION_PATH", Path(__file__).parent.parent.parent.parent.parent)) / "docs"
).resolve()

logger = get_logger(__file__)


@generate_swagger_docs(responses={200: "A markdown file containing documentation"})
@static_api.route("/docs", methods=["GET"])
@api_login()
def serve_documentation(**kwargs) -> dict[str, str]:
    """Returns all documentation or filtered documentation if given a url param of a file name or a path

    Variables:
    None

    Arguments:
    None

    Result Example:
    URL Link: /api/v1/static/docs?filter="howler"

    {"howler-docs.md": "Markdown documentation of howler-docs.md"}

    """
    docs_filter = request.args.get("filter")

    documentation_folder = Path.cwd() / "docs"

    returned_files = {}

    if docs_filter is None:
        for file in documentation_folder.rglob("*"):
            if file.is_file():
                content = file.read_text(encoding="utf-8")
                returned_files[file.name] = content
    else:
        for file in documentation_folder.rglob("*"):
            if file.is_file() and docs_filter in file.name:
                try:
                    content = file.read_text(encoding="utf-8")
                    returned_files[file.name] = content
                except FileNotFoundError:
                    return not_found(err="The file was not found")

    return ok(returned_files)


@generate_swagger_docs(responses={200: "A markdown file containing documentation"})
@static_api.route("/docs/<path:filename>", methods=["GET"])
@api_login()
def serve_documentation_file(filename: str, **kwargs) -> dict[str, str]:
    """Returns the specific file asked for within the route param

    Variables:
    filename (str): the specific file requested with an extension (i.e. *.md)

    Arguments:
    None

    Result Example:
    URL Link: /api/v1/static/docs/howler-docs.md

    {"markdown": "Markdown documentation of howler-docs.md"}

    """
    docs_path = (DOCUMENTATION_FOLDER / filename).resolve()

    if not docs_path.suffix:
        # Assume it's markdown
        filename = filename + ".md"

    if is_path_traversal(DOCUMENTATION_FOLDER, docs_path):
        return not_found(err="The file does not exist or is typed incorrectly.")

    if docs_path.exists():
        content = docs_path.read_text(encoding="utf-8")

        return ok({"markdown": content})

    logger.info("File %s does not exist", docs_path)
    return not_found(err="The file does not exist or is typed incorrectly.")
