from assemblyline_client.v4_client.client import Client
from clue.models.actions import ExecuteRequest
from pydantic import Field
from pydantic_core import Url

from .consts import AL_URL_BASE, CLASSIFICATION


class SubmitUrl(ExecuteRequest):
    """Extended ExecuteRequest for URL submission actions.

    Adds an additional parameter to control whether internet-connected
    analysis should be enabled when submitting URLs to Assemblyline.

    Attributes:
        internet_connected: Whether to enable internet-connected analysis
    """

    internet_connected: bool = Field(description="If internet connected analysis should be enabled", default=False)


def submit_url(client: Client, url: str, internet_connected: bool) -> tuple[Url, str]:
    """Submits a URL and returns a link to the submission."""
    # Get the user's default submission parameters as this contains details services
    # to enable, alert parameters, TTL, etc
    submission_params = client.user.submission_params(client.current_user)

    # Mutate with local state
    submission_params["classification"] = CLASSIFICATION
    submission_params["description"] = "Forwarded from Clue"
    del submission_params["submitter"]  # This will be filled in by AL and is messy when proxying user creds

    if internet_connected:
        submission_params["services"]["selected"].append("Internet Connected")

    result = client.submit(url=url, params=submission_params)

    sid = result["sid"]
    report_url = Url(f"{AL_URL_BASE}/submission/detail/{sid}")
    return (report_url, sid)
