from typing import Any

from flask import request
from flask_cors import CORS
from pydantic import TypeAdapter

from clue.api import forbidden, make_subapi_blueprint, ok
from clue.common.logging import get_logger
from clue.common.swagger import generate_swagger_docs
from clue.config import config
from clue.models.mongodb import ChangeRow
from clue.security import api_login
from clue.services import mongo_service

SUB_API = "sync"
sync_api = make_subapi_blueprint(SUB_API, api_version=1)
sync_api._doc = "Replication functionality for RxDB"  # type: ignore

CORS(sync_api, origins=config.ui.cors_origins, supports_credentials=True)

logger = get_logger(__file__)


@generate_swagger_docs()
@sync_api.route("/<collection>", methods=["GET"])
@api_login()
def pull(collection: str, user: dict[str, Any] | None = None, **kwargs) -> dict[str, str]:
    """Returns all documentation or filtered documentation if given a url param of a file name or a path

    Variables:
    None

    Arguments:
    None

    Result Example:
    URL Link: /api/v1/static/docs?filter="howler"

    {"howler-docs.md": "Markdown documentation of howler-docs.md"}

    """
    if not user:
        return forbidden(err="You must we logged in as a valid user.")

    updated_at = request.args.get("updated_at", 0, type=int)
    id: str | None = request.args.get("id", None)
    limit = request.args.get("limit", 10, type=int)

    return ok(mongo_service.pull(user["uname"], id, updated_at, batch_size=limit))


@generate_swagger_docs()
@sync_api.route("/<collection>", methods=["POST"])
@api_login()
def push(collection: str, user: dict[str, Any] | None = None, **kwargs) -> dict[str, str]:
    """Returns all documentation or filtered documentation if given a url param of a file name or a path

    Variables:
    None

    Arguments:
    None

    Result Example:
    URL Link: /api/v1/static/docs?filter="howler"

    {"howler-docs.md": "Markdown documentation of howler-docs.md"}

    """
    if not user:
        return forbidden(err="You must we logged in as a valid user.")

    change_rows = TypeAdapter(list[ChangeRow]).validate_python(request.json, strict=True, by_alias=True)

    return ok(mongo_service.push(user["uname"], change_rows))
