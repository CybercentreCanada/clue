from assemblyline_client.common.classification import Classification
from assemblyline_client.v4_client.client import Client
from clue.models.actions import ExecuteRequest
from consts import AL_URL_BASE
from pydantic import Field
from pydantic_core import Url


class SubmitUrl(ExecuteRequest):
    """Extended ExecuteRequest for URL submission actions.

    Adds an additional parameter to control whether internet-connected
    analysis should be enabled when submitting URLs to Assemblyline.

    Attributes:
        internet_connected: Whether to enable internet-connected analysis
    """

    internet_connected: bool = Field(description="If internet connected analysis should be enabled", default=False)


def submit_url(client: Client, c12n_engine: Classification, request: SubmitUrl) -> tuple[Url, str]:
    """Submits a URL and returns a link to the submission."""
    # Get the user's default submission parameters as this contains details services
    # to enable, alert parameters, TTL, etc
    submission_params = client.user.submission_params(client.current_user)

    # Mutate with local state
    submission_params["classification"] = request.selector.classification
    submission_params["description"] = "Forwarded from Clue"
    del submission_params["submitter"]  # This will be filled in by AL and is messy when proxying user creds

    # If the request is for internet-connected analysis,
    # ensure that the classification is not above the maximum allowed for submission with internet access
    if (
        request.internet_connected
        and c12n_engine.min_classification(request.selector.classification, c12n_engine.RESTRICTED)
        != c12n_engine.RESTRICTED
    ):
        submission_params["services"]["selected"].append("Internet Connected")

    result = client.submit(url=request.selector.value, params=submission_params)

    sid = result["sid"]
    report_url = Url(f"{AL_URL_BASE}/submission/detail/{sid}")
    return (report_url, sid)
