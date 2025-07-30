# ruff: noqa: D101
import hashlib
import textwrap
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr
from math import floor
from random import randbytes, sample
from typing import Any, Literal, Optional, Union

from pydantic import (
    AliasGenerator,
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_core import Url
from typing_extensions import Self

from clue.common.logging import get_logger
from clue.config import CLASSIFICATION, DEBUG, get_version
from clue.constants.supported_types import SUPPORTED_TYPES
from clue.models.validators import validate_classification

logger = get_logger(__file__)


class ClueResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(serialization_alias=lambda field_name: f"api_{field_name}")
    )

    response: Any = None
    error_message: Optional[str] = None
    warning: list[str] = []
    server_version: str = get_version()
    status_code: int


class Annotation(BaseModel):
    analytic: Optional[str] = Field(
        description="Identifier for the analytic producing the knowledge. Mutually exclusive with author.",
        default=None,
        examples=["Howler", "Assemblyline", None],
    )
    analytic_icon: Optional[str] = Field(
        description="Formatted string to present an icon for this analytic on the UI using iconify/react format: "
        "https://iconify.design/docs/icon-components/react/. External icons not yet supported",
        default=None,
        examples=["material-symbols:sound-detection-dog-barking", None],
    )
    author: Optional[str] = Field(
        description="The author providing the annotation. Mutually exclusive with analytic.",
        default=None,
        examples=["John Smith", None],
    )
    quantity: int = Field(
        description="Number of times this annotation was generated for the given indicator",
        default=1,
        examples=[1, 10, 25],
    )
    version: Optional[str] = Field(
        description="The version of the API for the analytic that produced the knowledge",
        default=None,
        examples=["v0.0.1", "1.0.0", None],
    )
    timestamp: Optional[datetime] = Field(
        description="A timestamp describing when the knowledge was generated.",
        default_factory=lambda: datetime.now(timezone.utc),
        examples=[datetime.now(timezone.utc), datetime.now(timezone.utc) - timedelta(weeks=2)],
    )
    type: Literal["opinion", "frequency", "assessment", "mitigation", "context"] = Field(
        description=textwrap.dedent("""
                                    What type of annotation is this?
                                    Opinion (What type of activity is the selector associated with?):
                                        benign - authorized or harmless activity
                                        suspect - outlier activity without clear intent
                                        malicious - intended to cause harm
                                        obscure - why a reliable opinion might not be possible

                                    Context (Unopinionated facts)
                                        Examples:
                                        - Frequency of observation based on summaries
                                        - Account privileges
                                        - Sign-in characteristics
                                        - Geo-location
                                        - Domain ownership
                                        - Operation Label

                                    Assessment (An official position)
                                        Benign Alert Assessments:
                                        - Ambiguous
                                        - Security
                                        - Development
                                        - False-positive
                                        - Legitimate

                                        Malicious Alert Assessments:
                                        - Trivial
                                        - Recon
                                        - Attempt
                                        - Compromise
                                        - Mitigated

                                    Frequency (A numeric value for the frequency a selector has been seen)
                                        Higher number - more common selector
                                        Lower number - less common selector

                                    Mitigation (Suggested actions available to mitigate harm done by the selector)
                                        exempt - Selector cannot be mitigated, used for known safe selectors
                                        alertable - Selector can be alerted on
                                        blockable - Selector can be blocked
                                        shareable - Selector can be shared with partners/collaborators
                                        not-alertable - Selector cannot be alerted on
                                        not-blockable - Selector cannot be blocked
                                        not-shareable - Selector cannot be shared with partners/collaborators
                                    """),
        examples=["opinion", "frequency", "assessment", "mitigation", "context"],
    )
    value: Union[str, float, int] = Field(
        description="The value associated with the type.",
        examples=[
            "benign",
            "suspect",
            "malicious",
            "obscure",
            "IP Located in Canada",
            "Involved in Operation Cat",
            11,
            42.0,
        ],
    )
    confidence: float = Field(
        description="Self-reported confidence level of the annotation. 0.0 = not confident at all, 1.0 = absolute fact",
        ge=0.0,
        le=1.0,
        examples=[0.0, 0.5, 1.0],
    )
    severity: Optional[float] = Field(
        description="Severity of the annotation, if accurate. 0.0 = not severe at all, 1.0 = extremely important",
        ge=0.0,
        le=1.0,
        default=None,
        examples=[0.0, 0.5, 1.0, None],
    )
    priority: Optional[float] = Field(
        description=(
            "What priority to assign to this annotation. Higher priority = more likely to be shown to analysts. "
            "Optional. If not provided, calculated based on confidence, severity and reliability."
        ),
        default=None,
        examples=[1.0, 50.0, 1000.0, None],
    )
    summary: str = Field(
        description="A plaintext summary of the annotation.",
        examples=["Example summary of the information in this Annotation"],
    )
    details: Optional[str] = Field(
        description="detailed description of the annotation. Supports markdown formatting.",
        default=None,
        examples=["# Here's some annotation details\n\nIt's very interesting", None],
    )
    link: Optional[Url] = Field(
        description="Link for more information about this specific annotation",
        default=None,
        examples=[Url("https://example.com/annotation"), None],
    )
    icon: Optional[str] = Field(
        description="Formatted string to present an icon for this annotation on the UI using iconify/react format: "
        "https://iconify.design/docs/icon-components/react/. External icons not yet supported",
        default=None,
        examples=["material-symbols:sound-detection-dog-barking", None],
    )
    ubiquitous: bool = Field(
        description="Does this annotation show up on the vast majority of selectors (i.e. asset provenance, "
        "organization ownership/non-ownership of IP address)",
        default=False,
        examples=[True, False],
    )

    @computed_field  # type: ignore[misc]
    @property
    def reliability(self: Self) -> Optional[float]:
        """Accurately calculated reliability of the annotation. 0.0 = not reliable, 1.0 = extremely reliable"""
        if self.author:
            return 1.0

        # TODO: Implement a way to set reliability of annotations from analytics
        return None

    @model_validator(mode="after")
    def validate_model(self: Self) -> Self:  # noqa: C901
        """Validates the entire model.

        Raises:
            AssertionError: Raised whenever a field is invalid on the model.

        Returns:
            Self: The validated model.
        """
        if not (self.author or self.analytic):
            raise AssertionError("Author or analytic must be set.")
        if self.author and self.analytic:
            raise AssertionError("Author and analytic are mutually exclusive.")

        if self.type in ["opinion", "assessment", "mitigation", "context"]:
            if not isinstance(self.value, str):
                raise AssertionError(
                    f"Value must be a string if type is not frequency. Type is ({type(self.value).__name__})"
                )
        else:
            try:
                self.value = int(self.value)
            except Exception as e:
                raise AssertionError("Value must be an int if type is frequency.") from e

        if self.type == "opinion":
            valid_options = ["benign", "suspicious", "malicious", "obscure"]
            if self.value not in valid_options:
                raise AssertionError(
                    f"If type is opinion, value must be one of ({', '.join(valid_options)}). Value is {self.value}"
                )

        elif self.type == "mitigation":
            valid_options = [
                "exempt",
                "alertable",
                "blockable",
                "shareable",
                "not-alertable",
                "not-blockable",
                "not-shareable",
            ]
            if self.value not in valid_options:
                raise AssertionError(
                    f"If type is mitigation, value must be one of ({', '.join(valid_options)}). Value is {self.value}"
                )

        elif self.type == "assessment":
            valid_options = [
                "ambiguous",
                "security",
                "development",
                "false-positive",
                "legitimate",
                "trivial",
                "recon",
                "attempt",
                "compromise",
                "mitigated",
            ]
            if self.value not in valid_options:
                raise AssertionError(
                    f"If type is assessment, value must be one of ({', '.join(valid_options)}). Value is {self.value}"
                )

        if self.icon and self.type != "context":
            raise AssertionError("Icons are currently only supported for 'context' annotations.")

        if self.icon and len(self.icon.split(":")) != 2:
            raise AssertionError("Icon field not formatted correctly. Must be in the format <icon_type>:<icon_id>.")

        if self.analytic_icon and len(self.analytic_icon.split(":")) != 2:
            raise AssertionError(
                "Analytic Icon field not formatted correctly. Must be in the format <icon_type>:<icon_id>."
            )

        if not self.priority and self.severity:
            modifier = self.reliability if self.reliability is not None else self.confidence

            # TODO: Tweak this behaviour as we have a better idea how it should behave.
            # Always outputs a priority in the range [0, 1]
            self.priority = modifier * (self.severity ** (2 - modifier))

        return self


class QueryEntry(BaseModel):
    classification: str = Field(
        description="Classification of results by the enrichment",
        default="TLP:CLEAR",
        examples=sample(sorted(CLASSIFICATION.list_all_classification_combinations()), k=5),
    )
    count: int = Field(
        description="Number of matches from the search",
        default=1,
        examples=sorted([floor(i / 10) for i in randbytes(5)]),  # noqa: S311
    )
    link: Optional[Url] = Field(
        description="Link to more information", default=None, examples=[Url("https://example.com/moreinfo"), None]
    )
    annotations: list[Annotation] = Field(
        description="A list of annotations returned from the service for this entry", default=[]
    )
    raw_data: Any = Field(
        description="The raw records associated with the generated annotations.",
        default=None,
        examples=[{"id": 1, "raw_field": "some_data"}, [{"id": 1, "other_data": "example", "other_row": 45}]],
    )

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("classification")
    @classmethod
    def check_classification(cls, classification: str) -> str:  # noqa: ANN102
        """Validates the provided classification.

        Args:
            classification (str): The classification to validate.

        Raises:
            AssertionError: Raised whenever the provided classification is not valid.

        Returns:
            str: The validated classification.
        """
        return validate_classification(classification)


class QueryResult(BaseModel):
    type: str = Field(
        description="The type of the value represented by this result", examples=list(SUPPORTED_TYPES.keys())
    )
    value: str = Field(
        description="The value represented by this result",
        examples=["127.0.0.1", "email@example.com", hashlib.sha256("example".encode()).hexdigest()],
    )
    source: str = Field(description="The name of the plugin providing this result", examples=["example_plugin"])
    error: Optional[str] = Field(
        description="Error message returned by data source",
        default=None,
        examples=["An error occurred when enriching the data.", None],
    )
    items: list[QueryEntry] = Field(description="List of results from the source", default=[])
    maintainer: Optional[str] = Field(
        description="Email contact in the RFC-5322 format 'Full Name <email_address>'.",
        default=None,
        examples=["maintainer@example.com", None],
    )
    datahub_link: Optional[Url] = Field(
        description="Link to datahub entry on this enrichment",
        default=None,
        examples=[Url("https://example.com/datahub"), None],
    )
    documentation_link: Optional[Url] = Field(
        description="Link to documentation on this enrichment",
        default=None,
        examples=[Url("https://example.com/documentation"), None],
    )
    latency: float = Field(
        description="Total duration (in milliseconds) taken to resolve this result",
        default=0,
        examples=sorted([i * 10 for i in randbytes(5)]),  # noqa: S311
    )

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("maintainer")
    @classmethod
    def validate_maintainer(cls, maintainer: Optional[str]) -> Optional[str]:  # noqa: ANN102
        """Validates the maintainer field.

        Args:
            maintainer (Optional[str]): The maintainer field to validate. If None, it will be passed through.

        Raises:
            AssertionError: Raised whenever the field is in an invalid format.

        Returns:
            Optional[str]: The validated maintainer field.
        """
        if maintainer:
            parsed_addr = parseaddr(maintainer)
            if not (all(parsed_addr) and "@" in parsed_addr[1]):
                raise AssertionError("Maintainer string must be in RFC-5322 format.")

        return maintainer

    @field_validator("items")
    @classmethod
    def validate_items(cls, items: list[QueryEntry], info: ValidationInfo) -> list[QueryEntry]:  # noqa: ANN102
        """Validate that if classification data was provided, all annotations match the user's classification.

        Args:
            items (list[QueryEntry]): The items to validate.
            info (ValidationInfo): Additional validation info.

        Returns:
            list[QueryEntry]: The validated items field.
        """
        if info.context:
            user_classification = info.context.get("user", {}).get("classification", None)
            if user_classification:
                filtered_results: list[QueryEntry] = []

                for item in items:
                    if CLASSIFICATION.is_accessible(user_classification, item.classification):
                        filtered_results.append(item)
                    else:
                        logger.debug(
                            "Removing item at classification %s, inaccessible to user classification %s",
                            item.classification,
                            user_classification,
                        )

                if len(items) > len(filtered_results):
                    logger.info(
                        "Dropped %s items due to inaccessible classification (user classification: %s)",
                        len(items) - len(filtered_results),
                        user_classification,
                    )
                elif DEBUG:
                    logger.debug(
                        "All %s values are accessible by user classification %s", len(items), user_classification
                    )

                return filtered_results
            else:
                logger.warning("No user classification given, classification parsing will not occur")
        else:
            logger.warning("No user context given, classification parsing will not occur")

        return items


class PluginResponse(BaseModel):
    pass
