# ruff: noqa: D101


from pydantic import Field

from clue.models.results.base import Result


class FileResult(Result):
    @staticmethod
    def format():
        "Return the clue format for this result"
        return "file"

    data: str = Field(description="The base64-encoded file data")
    mime_type: str = Field(
        description="The mime-type of the returned file (optional, defaults to application/octet-stream)",
        default="application/octet-stream",
    )
    file_name: str | None = Field(description="The file name", default=None)
