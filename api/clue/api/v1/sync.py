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
    """Pull replicated changes from a collection since a specified checkpoint.

    Variables:
    collection => The name of the collection to pull from.

    Optional Arguments:
    updated_at: int     => Timestamp of the last checkpoint. [Default: 0]
    id: string          => Document ID of the last checkpoint for pagination.
    limit: int          => Maximum number of records to return per batch. [Default: 10]
    omit_deleted        => If present, omit deleted records from the results.

    Result Example:
    [   # List of SelectorDocument records since the given checkpoint
        {
            "id": "<document id>",
            "updated_at": 1234567890,
            "_deleted": false,
            ...
        },
        ...
    ]
    """
    if not user:
        return forbidden(err="You must be logged in as a valid user.")

    if collection not in mongo_service.ALLOWED_COLLECTIONS:
        return bad_request(err=f"Unknown collection: {collection}")

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

    Variables:
    collection => The name of the collection to stream from.

    Arguments:
    None

    Result Example:
    # A continuous text/event-stream (SSE) of JSON-encoded change events:
    {"id": "<event id>", "documents": [{...}, ...], "checkpoint": {"id": "<id>", "updated_at": 1234567890}}
    """
    if not user:
        return forbidden(err="You must be logged in as a valid user.")

    if collection not in mongo_service.ALLOWED_COLLECTIONS:
        return bad_request(err=f"Unknown collection: {collection}")

    logger.info("Initializing event source stream")

    return mongo_service.event_stream(user["uname"], collection)


@generate_swagger_docs()
@sync_api.route("/<collection>", methods=["POST"])
@api_login()
def push(collection: str, user: dict[str, Any] | None = None, **kwargs) -> dict[str, str]:
    """Push replicated changes to a collection.

    Variables:
    collection => The name of the collection to push to.

    Arguments:
    None

    Data Block:
    [   # List of change rows for RxDB replication
        {
            "newDocumentState": {   # Required. The new state of the document.
                "id": "<document id>",
                "updated_at": 1234567890,
                "_deleted": false,
                ...
            },
            "assumedMasterState": { # Optional. The assumed current server state for conflict detection.
                "id": "<document id>",
                "updated_at": 1234567890,
                ...
            }
        },
        ...
    ]

    Result Example:
    [   # List of conflicting SelectorDocuments that were not applied
        {
            "id": "<document id>",
            "updated_at": 1234567890,
            "_deleted": false,
            ...
        },
        ...
    ]
    """
    if not user:
        return forbidden(err="You must be logged in as a valid user.")

    if collection not in mongo_service.ALLOWED_COLLECTIONS:
        return bad_request(err=f"Unknown collection: {collection}")

    try:
        change_rows = TypeAdapter(list[ChangeRow]).validate_python(request.json, strict=True, by_alias=True)

        return ok(mongo_service.push(user["uname"], collection, change_rows))
    except ValidationError:
        logger.exception("Validation exception on push")
        return bad_request(err="Invalid replication data.")
    except Exception:
        return internal_error(err="Failed to process replication data.")
