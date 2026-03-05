import json
import time

from dotenv import load_dotenv
from flask import Response
from redis.client import PubSub

from clue.models.config import ExternalSource
from clue.models.selector import Selector

load_dotenv()

from typing import Any

from pymongo import DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure

from clue.common.exceptions import ClueRuntimeError, ClueValueError
from clue.common.logging import get_logger
from clue.config import config, get_redis
from clue.models.schema import get_bson_schema
from clue.models.sync import ChangeRow, Checkpoint, PublishEvent, SelectorDocument

logger = get_logger(__file__)

MONGO_CLIENT: MongoClient | None = None
ALLOWED_COLLECTIONS: frozenset[str] = frozenset(["selectors"])
INITIALIZED_COLLECTIONS: set[str] = set()

REDIS_EVENT_ID_KEY = "clue:event_id"
_CONNECT_MAX_ATTEMPTS = 4
_CONNECT_BACKOFF_BASE = 0.5  # seconds; delay = base * 2^attempt


def _get_event_id() -> int:
    """Return a monotonically increasing event ID backed by Redis INCR.

    Using Redis ensures the counter is shared across all Flask workers and pods.

    Returns:
        int: A unique, monotonically increasing event ID.
    """
    return int(get_redis().incr(REDIS_EVENT_ID_KEY))


def _connect() -> MongoClient:
    """Return a live MongoClient, creating or replacing it as needed.

    On the first call, or after a failed ping, creates a new MongoClient and
    retries up to _CONNECT_MAX_ATTEMPTS times with exponential backoff.

    Raises:
        ClueRuntimeError: If the connection cannot be established after all retries.
    """
    global MONGO_CLIENT

    last_exc: Exception | None = None
    for attempt in range(_CONNECT_MAX_ATTEMPTS):
        if MONGO_CLIENT is None or attempt > 0:
            logger.info(
                "Connecting to %s (attempt %s/%s)",
                repr(config.core.mongodb),
                attempt + 1,
                _CONNECT_MAX_ATTEMPTS,
            )
            MONGO_CLIENT = MongoClient(**config.core.mongodb.connection())  # type: ignore

        try:
            MONGO_CLIENT.admin.command("ping")
            return MONGO_CLIENT
        except ConnectionFailure as e:
            last_exc = e
            if attempt < _CONNECT_MAX_ATTEMPTS - 1:
                delay = _CONNECT_BACKOFF_BASE * (2**attempt)
                logger.warning(
                    "MongoDB connection failed (attempt %s/%s), retrying in %.1fs...",
                    attempt + 1,
                    _CONNECT_MAX_ATTEMPTS,
                    delay,
                )
                time.sleep(delay)

    raise ClueRuntimeError("Failed to connect to MongoDB after all retries.") from last_exc


def _get_collection(user: str, collection: str) -> Collection[dict[str, Any]]:
    """Get or create a MongoDB collection for the specified user.

    Args:
        user (str): The username to use as the first portion of the collection name.
        collection (str): The username to use as the second portion of the collection name.

    Returns:
        Collection: The MongoDB collection for the user.

    Raises:
        ClueValueError: If the collection name is not in ALLOWED_COLLECTIONS.
        ClueRuntimeError: If no MongoDB host is specified in the configuration, or if
            reconnection after a lost connection fails.
    """
    if collection not in ALLOWED_COLLECTIONS:
        raise ClueValueError(f"Unknown collection: {collection}")

    if not config.ui.replication:
        logger.warning("Replication is not enabled - why is mongodb being initialized?")

    if not config.core.mongodb.host:
        raise ClueRuntimeError("No mongodb host specified.")

    client = _connect()

    collection_name = f"{user}-{collection}"

    database = client[config.core.mongodb.database]
    if collection_name not in INITIALIZED_COLLECTIONS and collection_name not in database.list_collection_names():
        database.create_collection(collection_name, validator=get_bson_schema(SelectorDocument))

        # indexes to help speed up rxdb-related pulls.
        database[collection_name].create_index([("updated_at", DESCENDING)], name="rxdb::updated_at")
        database[collection_name].create_index([("updated_at", DESCENDING), "id"], name="rxdb::updated_at+id")

        INITIALIZED_COLLECTIONS.add(collection_name)

    return database[collection_name]


def build_pubsub() -> PubSub:
    """Build and return a Redis PubSub client.

    Returns:
        PubSub: A Redis PubSub client instance.
    """
    client = get_redis()
    return client.pubsub()


def event_stream(user: str, collection: str) -> Response:
    """Stream selector events for a user via Server-Sent Events.

    Args:
        user (str): The username to stream events for.
        collection (str): The collection to stream events for.

    Returns:
        Response: A Flask response with text/event-stream mimetype for SSE.

    Raises:
        ClueValueError: If the collection name is not in ALLOWED_COLLECTIONS.
    """
    if collection not in ALLOWED_COLLECTIONS:
        raise ClueValueError(f"Unknown collection: {collection}")

    pubsub = build_pubsub()
    pubsub.subscribe(f"{user}-{collection}")

    def stream():
        try:
            for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                event_id = _get_event_id()
                event = {"id": event_id, **json.loads(message["data"].decode())}

                logger.info("Writing event (id:%s)", event_id)
                yield json.dumps(event) + "\n"
        finally:
            pubsub.close()

    return Response(stream(), mimetype="text/event-stream")


def push(user: str, collection: str, change_rows: list[ChangeRow]) -> list[SelectorDocument]:
    """Push change rows to the MongoDB collection and return conflicts.

    Args:
        user (str): The username to use as the collection name.
        change_rows (list[ChangeRow]): List of change rows to push to the collection.

    Returns:
        list[SelectorDocument]: List of conflicting documents encountered during the push.
    """
    logger.debug(
        "Pushing records from mongodb for user %s to collection %s (%s records)",
        user,
        collection,
        len(change_rows),
    )
    conflicts: list[SelectorDocument] = []
    event = PublishEvent()

    user_collection = _get_collection(user, collection)

    with user_collection.database.client.start_session() as session:
        with session.start_transaction():
            try:
                for row in change_rows:
                    existing_record = user_collection.find_one({"id": row.new_document_state.id}, session=session)

                    existing_selector: SelectorDocument | None = None
                    if existing_record:
                        existing_selector = SelectorDocument.model_validate(existing_record)

                        if not row.assumed_master_state:
                            conflicts.append(existing_selector)
                            continue
                        elif (
                            row.assumed_master_state
                            and existing_selector.updated_at != row.assumed_master_state.updated_at
                        ):
                            conflicts.append(existing_selector)
                            continue

                    data = row.new_document_state.model_dump(mode="json", by_alias=True)
                    user_collection.replace_one(
                        {"id": row.new_document_state.id},
                        data,
                        upsert=True,
                        session=session,
                    )
                    event.documents.append(row.new_document_state)
                    event.checkpoint = Checkpoint(
                        id=row.new_document_state.id,
                        updated_at=row.new_document_state.updated_at,
                    )
            except Exception:
                logger.exception("Exception on push transacation to %s-%s", user, collection)
                session.abort_transaction()
                raise

    if len(event.documents) > 0:
        logger.info("Publishing event")
        get_redis().publish(f"{user}-{collection}", event.model_dump_json(by_alias=True, exclude_none=True))

    if len(conflicts) > 0:
        logger.info("Returning %s conflicts", len(conflicts))

    return conflicts


def pull(user: str, collection: str, id: str | None, updated_at: int, batch_size: int, omit_deleted: bool = False):
    """Pull records from MongoDB collection using checkpoint-based pagination.

    Retrieves a batch of records from a user's MongoDB collection, starting from
    a checkpoint defined by the last updated_at timestamp and id. Records are
    sorted by updated_at and id to ensure consistent pagination across requests.

    Args:
        user (str): The username to identify the MongoDB collection.
        collection (str): The collection name within the user's database.
        id (str | None): The record id portion of the checkpoint for pagination.
        updated_at (int): The last updated timestamp of the checkpoint.
        batch_size (int): The maximum number of records to return.
        omit_deleted (bool, optional): If True, exclude deleted records from results. Defaults to False.

    Returns:
        list[SelectorDocument]: A list of validated SelectorDocument models retrieved from MongoDB,
            ordered by updated_at and id, limited to batch_size records.
    """
    logger.info(
        "Pulling records from mongodb for user %s in collection %s (checkpoint: id=%s, updated_at=%s) limit %s",
        user,
        collection,
        id,
        updated_at,
        batch_size,
    )

    query: dict[str, list | bool] = {
        "$or": [
            {
                "updated_at": {"$gt": updated_at},
            },
            {"updated_at": updated_at, "id": id},
        ]
    }

    if omit_deleted:
        query["_deleted"] = False

    query_result = _get_collection(user, collection).find(query).sort(["updated_at", "id"]).limit(batch_size).to_list()

    models: list[SelectorDocument] = [SelectorDocument.model_validate(record) for record in query_result]

    logger.info("Returning %s documents", len(models))

    return models


def existing_results(user: str, collection: str, selectors: list[Selector], external_sources: list[ExternalSource]):
    """Check if documents matching the specified selectors and sources exist in the user's collection.

    Args:
        user (str): The username to use as the collection name.
        collection (str): The collection name within the user's database.
        selectors (list[Selector]): List of selectors (type/value pairs) to search for.
        external_sources (list[ExternalSource]): List of external sources to filter by.

    Returns:
        dict: A dictionary mapping source names to lists of matching records (type/value pairs).
    """
    if not config.ui.replication:
        return {}

    try:
        types = [selector.type for selector in selectors]
        values = [selector.value for selector in selectors]
        sources = [source.name for source in external_sources]

        raw_result = (
            _get_collection(user, collection)
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
    except ClueRuntimeError:
        # ClueRuntimeError if mongodb isn't functional - we'll silently fail so enrichment can continue
        return {}
