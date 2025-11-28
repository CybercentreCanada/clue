# ruff: noqa: D101
import ipaddress
import json
from typing import Annotated

from flask import request
from pydantic import BaseModel, Field, StringConstraints, model_validator
from typing_extensions import Self

from clue.common.logging import get_logger
from clue.config import CLASSIFICATION
from clue.constants.supported_types import CASE_INSENSITIVE_TYPES

logger = get_logger(__file__)


class Selector(BaseModel):
    type: Annotated[str, StringConstraints(to_lower=True, strip_whitespace=True)]
    value: str
    classification: str | None = Field(default=None)
    sources: list[str] | None = Field(default=None)

    @model_validator(mode="after")
    def validate_model(self: Self) -> Self:  # noqa: C901
        """Validates the entire model.

        Raises:
            AssertionError: Raised whenever a field is invalid on the model.

        Returns:
            Self: The validated model.
        """
        # For backwards compatability, if eml is used it is replaced with email
        self.type = self.type.replace("eml", "email")

        if self.type == "ip":
            is_ipv4 = isinstance(ipaddress.ip_address(self.value), ipaddress.IPv4Address)
            self.type = "ipv4" if is_ipv4 else "ipv6"

        if self.type == "telemetry":
            try:
                json.loads(self.value)
            except json.JSONDecodeError as e:
                raise AssertionError("If type is telemetry, value must be a valid JSON object.") from e
        elif self.type in CASE_INSENSITIVE_TYPES:
            self.value = self.value.lower()

        if not self.classification:
            try:
                self.classification = request.args.get("classification", CLASSIFICATION.UNRESTRICTED)
            except RuntimeError:
                pass

        if self.sources is None:
            try:
                if query_sources_str := request.args.get("sources", None):
                    if "|" in query_sources_str:
                        self.sources = query_sources_str.split("|")
                    else:
                        self.sources = query_sources_str.split(",")
            except RuntimeError:
                pass

        return self


BulkEnrich = Selector
