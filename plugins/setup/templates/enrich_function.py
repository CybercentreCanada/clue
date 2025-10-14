from clue.models.network import Annotation, QueryEntry
from clue.plugin.utils import Params
from pydantic_core import Url

# ---


@plugin.use  # type: ignore  # noqa: F821
def enrich(type_name: str, value: str, params: Params, token: str | None) -> QueryEntry:
    """Main enrichment function for processing selectors.

    This function accepts the type and value of a selector, along with parameters
    relevant to the enrichment and an authentication token from the central API.
    It returns QueryEntry object(s) containing enrichment data for the given selector.

    IMPORTANT: This function enriches one selector at a time, which makes it inefficient
    for bulk operations. For large datasets, consider implementing alternate_bulk_lookup
    instead. Using this function for many selectors will result in numerous individual
    queries (e.g., 100 single-selector queries instead of one bulk query with 100 selectors)
    which is particularly problematic with database systems like Trino, SQL databases,
    or APIs that support batch operations.

    Args:
        type_name: The type of the selector being enriched (e.g., 'ip', 'domain', 'hash')
        value: The actual value of the selector to enrich
        params: Parameters for the enrichment including limit and annotation preferences
        token: Authentication token from the central API (if authentication is enabled)

    Returns:
        QueryEntry: Object containing enrichment results including annotations,
                   classification, and metadata about the enriched selector
    """
    logger.info(f"Enriching [{type_name}] {value} limit {params.limit} (annotate={params.annotate})")  # type: ignore  # noqa: F821

    # QueryEntry represents a single enrichment result containing metadata about where the
    # annotations were generated. It includes the classification level of the results,
    # the count of matches found, optional links for more information, and the list of
    # annotations that provide the actual enrichment data. This serves as a container
    # that groups related annotations together with their source context.
    return QueryEntry(
        classification=CLASSIFICATION,  # type: ignore  # noqa: F821
        count=1,
        link=Url("https://example.com"),
        annotations=[
            # Annotations provide enrichment data that gets displayed in the UI as interactive cards.
            # They can represent different types of information: opinions (benign/malicious/suspect),
            # context (facts like geo-location, frequency), assessments (official positions),
            # mitigations (suggested actions), or frequency data. The UI groups annotations by type
            # and displays them in expandable sections with icons, confidence levels, and clickable
            # links for additional details. Each annotation includes a summary for quick viewing
            # and optional detailed markdown content.
            Annotation(
                analytic="Test Plugin",
                analytic_icon="fluent-color:checkmark-circle-16",
                icon="fluent-color:checkmark-circle-16",
                type="context",
                value=value,
                link=Url("https://example.com"),
                summary=f"Test Enrichment - type: {type_name}, value: {value}",
                confidence=1.0,
            )
        ],
    )
