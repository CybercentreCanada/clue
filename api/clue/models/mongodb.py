from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

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
    return int(datetime.now().timestamp())


class SelectorDocument(QueryEntry, ResultMetadata):
    """The document used for validating records in the rxdb replication context."""

    id: str = Field(description="The ID of the selector", default_factory=generate_uuid)
    updated_at: int = Field(description="The last updated time of this record", default_factory=generate_updated_at)
    deleted: bool = Field(description="Is this row 'deleted' by rxdb?", default=False, alias="_deleted")


class ChangeRow(BaseModel):
    """A change row for RxDB replication conflict resolution.

    Attributes:
        new_document_state: The new state of the document from RxDB.
        assumed_master_state: The optional assumed state of the document when responding to conflicts.
    """

    new_document_state: SelectorDocument
    "The new state of the document from RxDB"

    assumed_master_state: SelectorDocument | None
    "The optional assumed state of the document when responding to conflicts"
