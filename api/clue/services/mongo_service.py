from dotenv import load_dotenv

load_dotenv()

from typing import Any

from pymongo import MongoClient
from pymongo.synchronous.collection import Collection

from clue.common.exceptions import ClueRuntimeError
from clue.common.logging import get_logger
from clue.config import config
from clue.models.mongodb import ChangeRow, SelectorDocument
from clue.models.schema import get_bson_schema

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

    if user not in database.list_collection_names():
        database.create_collection(user, validator=get_bson_schema(SelectorDocument))

    return database[user]


def push(user: str, change_rows: list[ChangeRow]) -> list[SelectorDocument]:
    """Push change rows to the MongoDB collection and return conflicts.

    Args:
        user (str): The username to use as the collection name.
        change_rows (list[ChangeRow]): List of change rows to push to the collection.

    Returns:
        list[SelectorDocument]: List of conflicting documents encountered during the push.
    """
    conflicts: list[SelectorDocument] = []

    # TODO: Implement the pullStream

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

        user_collection.update_one({"id": row.new_document_state.id}, row.new_document_state.model_dump())

    return conflicts


def pull(user: str, id: str | None, updated_at: int, batch_size: int):
    """Initialize or retrieve the MongoDB collection for the specified user.

    Args:
        user (str): The username to use as the collection name.
        id (str): The record portion of the checkpoint.
        updated_at (int): The last updated time of the checkpoint.
    """
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

    return models


if __name__ == "__main__":
    records = [
        SelectorDocument(type="ip", value="1.1.1.1", source="test"),
        SelectorDocument(type="ip", value="1.1.1.1", source="test"),
        SelectorDocument(type="ip", value="1.1.1.1", source="test"),
    ]

    collection("goose").insert_many((record.model_dump(mode="json") for record in records), ordered=False)

    print(pull("goose", records[0].id, 0, batch_size=2))
