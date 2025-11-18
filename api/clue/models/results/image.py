# ruff: noqa: D101


from pydantic import Field

from clue.common.logging import get_logger
from clue.models.results.base import Result

logger = get_logger(__file__)


class ImageResult(Result):
    @staticmethod
    def format():
        "Return the clue format for this result"
        return "image"

    image: str = Field(
        description="An image URL, either redirecting to a valid network location or encoded image data in "
        "base64 format."
    )
    alt: str = Field(description="The label for the image.")
