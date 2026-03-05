from typing import Any

from flask import request
from flask_cors import CORS
from pydantic import TypeAdapter, ValidationError

from clue.api import bad_request, forbidden, internal_error, make_subapi_blueprint, ok
from clue.common.logging import get_logger
from clue.common.swagger import generate_swagger_docs
from clue.config import config
from clue.models.sync import ChangeRow
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
    """Pull replicated changes from a collection since a specified timestamp.

    Args:
        collection (str): The name of the collection to pull from.
        user (dict[str, Any] | None, optional): The authenticated user information. Defaults to None.
        **kwargs: Additional keyword arguments.

    Returns:
        dict[str, str]: A dictionary containing the replicated data with the following structure:
            - On success: Contains the pulled changes from the database.
            - On error: Contains an error message if the user is not authenticated.

    Raises:
        None: Returns a forbidden response if user is not authenticated.

    Note:
        Query parameters:
        - updated_at (int): Timestamp to filter changes since this update time. Defaults to 0.
        - id (str, optional): Optional document ID to filter results. Defaults to None.
        - limit (int): Maximum number of records to return per batch. Defaults to 10.
    """
    if not user:
        return forbidden(err="You must be logged in as a valid user.")

    updated_at = request.args.get("updated_at", 0, type=int)
    id: str | None = request.args.get("id", None)
    limit = request.args.get("limit", 10, type=int)
    omit_deleted = "omit_deleted" in request.args

    return ok(
        mongo_service.pull(user["uname"], collection, id, updated_at, batch_size=limit, omit_deleted=omit_deleted)
    )


@generate_swagger_docs()
@sync_api.route("/<collection>/stream", methods=["GET"])
@api_login()
def stream(collection: str, user: dict[str, Any] | None = None, **kwargs):
    """Stream replicated changes from a collection as server-sent events.

    Args:
        collection (str): The name of the collection to stream from.
        user (dict[str, Any] | None, optional): The authenticated user information. Defaults to None.
        **kwargs: Additional keyword arguments.

    Returns:
        Server-sent event stream containing replicated changes for the authenticated user.

    Raises:
        None: Returns a forbidden response if user is not authenticated.
    """
    if not user:
        return forbidden(err="You must be logged in as a valid user.")

    logger.info("Initializing event source stream")

    return mongo_service.event_stream(user["uname"], collection)


@generate_swagger_docs()
@sync_api.route("/<collection>", methods=["POST"])
@api_login()
def push(collection: str, user: dict[str, Any] | None = None, **kwargs) -> dict[str, str]:
    """Push replicated changes to a collection.

    Args:
        collection (str): The name of the collection to push to.
        user (dict[str, Any] | None, optional): The authenticated user information. Defaults to None.
        **kwargs: Additional keyword arguments.

    Returns:
        dict[str, str]: A dictionary containing the push result with the following structure:
            - On success: Contains the result of the push operation.
            - On error: Contains an error message if the user is not authenticated.

    Raises:
        None: Returns a forbidden response if user is not authenticated.
    """
    if not user:
        return forbidden(err="You must be logged in as a valid user.")

    try:
        change_rows = TypeAdapter(list[ChangeRow]).validate_python(request.json, strict=True, by_alias=True)
    except ValidationError:
        logger.exception("Validation exception on push")
        return bad_request(err="Invalid replication data.")

    try:
        return ok(mongo_service.push(user["uname"], collection, change_rows))
    except Exception:
        return internal_error(err="Failed to process replication data.")
