from datetime import datetime, timezone
from uuid import uuid4

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from clue.models.network import QueryEntry, ResultMetadata


def generate_uuid():
    """Generate a unique UUID string.

    Returns:
        str: A unique UUID as a string.
    """
    return str(uuid4())


def generate_updated_at():
    """Generate the current timestamp in seconds.

    Returns:
        int: The current timestamp as a unix epoch.
    """
    return int(datetime.now(tz=timezone.utc).timestamp())


class SelectorDocument(QueryEntry, ResultMetadata):
    """The document used for validating records in the rxdb replication context."""

    id: str = Field(default_factory=generate_uuid)
    "The ID of the selector"

    updated_at: int = Field(default_factory=generate_updated_at)
    "The last updated time of this record"

    deleted: bool = Field(default=False, alias="_deleted", serialization_alias="_deleted")
    "Is this row 'deleted' by rxdb?"


class ChangeRow(BaseModel):
    """A change row for RxDB replication conflict resolution.

    Attributes:
        new_document_state: The new state of the document from RxDB.
        assumed_master_state: The optional assumed state of the document when responding to conflicts.
    """

    new_document_state: SelectorDocument
    "The new state of the document from RxDB"

    assumed_master_state: SelectorDocument | None = None
    "The optional assumed state of the document when responding to conflicts"

    model_config = ConfigDict(
        alias_generator=AliasGenerator(validation_alias=to_camel, serialization_alias=to_camel),
        validate_assignment=True,
    )


class Checkpoint(BaseModel):
    """A checkpoint for RxDB replication tracking.

    Attributes:
        id: The ID of the checkpoint.
        updated_at: The timestamp when the checkpoint was last updated.
    """

    id: str
    "The ID of the checkpoint"

    updated_at: int
    "The timestamp when the checkpoint was last updated"


class PublishEvent(BaseModel):
    """A publish event for RxDB replication.

    Attributes:
        documents: The list of documents to publish.
        checkpoint: The optional checkpoint for tracking replication progress.
    """

    documents: list[SelectorDocument] = []
    "The list of documents to publish"

    checkpoint: Checkpoint | None = None
    "The optional checkpoint for tracking replication progress"
