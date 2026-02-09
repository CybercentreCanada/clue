import json

from dotenv import load_dotenv
from flask import Response
from redis.client import PubSub

from clue.models.config import ExternalSource
from clue.models.selector import Selector

load_dotenv()

from typing import Any

from pymongo import MongoClient
from pymongo.synchronous.collection import Collection

from clue.common.exceptions import ClueRuntimeError
from clue.common.logging import get_logger
from clue.config import config, get_redis
from clue.models.schema import get_bson_schema
from clue.models.sync import ChangeRow, Checkpoint, PublishEvent, SelectorDocument

logger = get_logger(__file__)

SERVER: MongoClient | None = None


def collection(user: str) -> Collection[dict[str, Any]]:
    """Get or create a MongoDB collection for the specified user.

    Args:
        user (str): The username to use as the collection name.

    Returns:
        Collection: The MongoDB collection for the user.

    Raises:
        ClueRuntimeError: If no MongoDB host is specified in the configuration.
    """
    global SERVER

    if not config.ui.replication:
        logger.warning("Replication is not enabled - why is mongodb being initialized?")

    if not config.core.mongodb.host:
        raise ClueRuntimeError("No mongodb host specified.")

    if SERVER is None:
        connection = repr(config.core.mongodb)
        logger.info("Connecting to %s", connection)
        SERVER = MongoClient(connection)

    database = SERVER[config.core.mongodb.database]

    collection_name = f"{user}-selectors"
    if collection_name not in database.list_collection_names():
        database.create_collection(collection_name, validator=get_bson_schema(SelectorDocument))

    return database[collection_name]


def build_pubsub() -> PubSub:
    """Build and return a Redis PubSub client.

    Returns:
        PubSub: A Redis PubSub client instance.
    """
    client = get_redis()
    return client.pubsub()


def event_stream(user: str) -> Response:
    """Stream selector events for a user via Server-Sent Events.

    Args:
        user (str): The username to stream events for.

    Returns:
        Response: A Flask response with text/event-stream mimetype for SSE.
    """
    pubsub = build_pubsub()
    pubsub.subscribe(f"{user}-selectors")

    def stream():
        event_id = 0
        for message in pubsub.listen():
            if message["type"] != "message":
                continue

            event = {"id": event_id, **json.loads(message["data"].decode())}

            event_id = event_id + 1

            logger.info("Writing event (id:%s)", event_id)
            yield json.dumps(event) + "\n"

    return Response(stream(), mimetype="text/event-stream")


def push(user: str, change_rows: list[ChangeRow]) -> list[SelectorDocument]:
    """Push change rows to the MongoDB collection and return conflicts.

    Args:
        user (str): The username to use as the collection name.
        change_rows (list[ChangeRow]): List of change rows to push to the collection.

    Returns:
        list[SelectorDocument]: List of conflicting documents encountered during the push.
    """
    logger.info(
        "Pushing records from mongodb for user %s (%s records)",
        user,
        len(change_rows),
    )
    conflicts: list[SelectorDocument] = []
    event = PublishEvent()

    user_collection = collection(user)

    for row in change_rows:
        existing_record = user_collection.find_one({"id": row.new_document_state.id})

        existing_selector: SelectorDocument | None = None
        if existing_record:
            existing_selector = SelectorDocument.model_validate(existing_record)

            if not row.assumed_master_state:
                conflicts.append(existing_selector)
                continue
            elif row.assumed_master_state and existing_selector.updated_at != row.assumed_master_state.updated_at:
                conflicts.append(existing_selector)
                continue

        data = row.new_document_state.model_dump(mode="json", by_alias=True)
        user_collection.replace_one(
            {"id": row.new_document_state.id},
            data,
            upsert=True,
        )
        event.documents.append(row.new_document_state)
        event.checkpoint = Checkpoint(id=row.new_document_state.id, updated_at=row.new_document_state.updated_at)

    if len(event.documents) > 0:
        logger.info("Publishing event")
        get_redis().publish(f"{user}-selectors", event.model_dump_json(by_alias=True, exclude_none=True))

    if len(conflicts) > 0:
        logger.info("Returning %s conflicts")

    return conflicts


def pull(user: str, id: str | None, updated_at: int, batch_size: int):
    """Initialize or retrieve the MongoDB collection for the specified user.

    Args:
        user (str): The username to use as the collection name.
        id (str): The record portion of the checkpoint.
        updated_at (int): The last updated time of the checkpoint.
    """
    logger.info(
        "Pulling records from mongodb for user %s (checkpoint: id=%s, updated_at=%s) limit %s",
        user,
        id,
        updated_at,
        batch_size,
    )

    query_result = (
        collection(user)
        .find(
            {
                "$or": [
                    {
                        "updated_at": {"$gt": updated_at},
                    },
                    {"updated_at": updated_at, "id": id},
                ]
            }
        )
        .sort(["updated_at", "id"])
        .limit(batch_size)
        .to_list()
    )

    models: list[SelectorDocument] = [SelectorDocument.model_validate(record) for record in query_result]

    logger.info("Returning %s documents", len(models))

    return models


def existing_results(user: str, selectors: list[Selector], external_sources: list[ExternalSource]):
    """Check if a document with the specified criteria exists in the user's collection.

    Args:
        user (str): The username to use as the collection name.
        type_name (str): The type of the document to search for.
        value (str): The value of the document to search for.
        source (str): The source of the document to search for.

    Returns:
        bool: True if a matching document exists, False otherwise.
    """
    types = [selector.type for selector in selectors]
    values = [selector.value for selector in selectors]
    sources = [source.name for source in external_sources]

    raw_result = (
        collection(user)
        .aggregate(
            [
                {
                    "$match": {
                        "type": {"$in": types},
                        "value": {"$in": values},
                        "source": {"$in": sources},
                        "_deleted": False,
                        "error": None,
                    }
                },
                {"$group": {"_id": "$source", "records": {"$push": {"type": "$type", "value": "$value"}}}},
            ]
        )
        .to_list()
    )

    return {entry["_id"]: entry["records"] for entry in raw_result}


if __name__ == "__main__":
    records = [
        SelectorDocument(type="ip", value="1.1.1.1", source="test"),
        SelectorDocument(type="ip", value="1.1.1.1", source="test"),
        SelectorDocument(type="ip", value="1.1.1.1", source="test"),
    ]

    collection("goose").insert_many(
        (record.model_dump(mode="json", by_alias=True) for record in records), ordered=False
    )

    print(pull("goose", records[0].id, 0, batch_size=2))  # noqa: T201
