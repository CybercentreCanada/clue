"""HBS GetFile Clue Plugin

Task HBS infrastructure to retrieve a kragle_file by path via the HBSI GetFile API.
Deduplicates by SHA256 — re-tasking the same file returns the existing trxId.

Analysts provide a justification and session ID (UI should persist these in localStorage).
"""

import json
import os
from typing import Optional, cast

import requests
from clue.common.exceptions import ClueException, InvalidDataException
from clue.common.logging import get_logger
from clue.models.actions import Action, ActionResult, ExecuteRequest
from clue.plugin import CluePlugin
from pydantic import Field

logger = get_logger(__file__)

CLASSIFICATION = os.environ.get("CLASSIFICATION", "PB")
TASKING_API_URL = os.environ.get("TASKING_API_URL", "https://tasking-api.pb.cyber.burrito.cloud")
VERIFY = os.environ.get("VERIFY", "true").lower() not in ("false", "0")
TIMEOUT = float(os.environ.get("TIMEOUT", 10))


class GetFileRequest(ExecuteRequest):
    # ponytail: cookie persistence for these fields is a UI concern (localStorage/sessionStorage)
    justification: str = Field(description="Necessity and proportionality justification.")
    session_id: str = Field(description="HBS session ID for this tasking.")


ACTIONS = [
    Action[GetFileRequest](
        id="get_file",
        name="Task File Retrieval",
        classification=CLASSIFICATION,
        summary="Task HBS infrastructure to retrieve this file via SA.GetFile",
        supported_types={"kragle_file"},
        action_icon="mdi:file-download",
    )
]

plugin = CluePlugin(
    app_name=os.environ.get("APP_NAME", "hbs-getfile"),
    classification=CLASSIFICATION,
    enable_apm=False,
    enable_cache=False,
    logger=logger,
    actions=ACTIONS,
)


@plugin.use
def run_action(action: Action, action_request: ExecuteRequest, token: Optional[str]) -> ActionResult:
    "Task the HBS infrastructure to retrieve the specified kragle_file"
    req = cast(GetFileRequest, action_request)

    if not req.selector:
        raise InvalidDataException("A kragle_file selector is required.")

    try:
        row = json.loads(req.selector.value)
    except (json.JSONDecodeError, TypeError) as e:
        raise InvalidDataException(f"kragle_file value must be a JSON-encoded row: {e}")

    agent_id = row.get("hbs_agent_id")
    path = row.get("NormalizedPath") or row.get("Path")
    sha256 = (row.get("Hash") or {}).get("SHA256")

    missing = [k for k, v in [("hbs_agent_id", agent_id), ("Path", path), ("Hash.SHA256", sha256)] if not v]
    if missing:
        raise InvalidDataException(f"kragle_file row is missing required fields: {', '.join(missing)}")

    payload = {
        "filename": path,
        "destinationAgentId": agent_id,
        "digest": sha256,
        "digestType": "sha256",
        "sessionId": req.session_id,
        "taskingOptions": {"justification": req.justification},
    }

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.post(
            f"{TASKING_API_URL}/api/tasking/getfile",
            json=payload,
            headers=headers,
            verify=VERIFY,
            timeout=TIMEOUT,
        )
    except requests.exceptions.Timeout as e:
        raise ClueException("HBSI tasking API timed out", cause=e)
    except requests.exceptions.RequestException as e:
        raise ClueException(f"Failed to reach HBSI tasking API: {e}", cause=e)

    if not resp.ok:
        raise ClueException(f"HBSI API returned [{resp.status_code}]: {resp.text[:300]}")

    result = resp.json()
    trx_id = result.get("trxId", -1)
    success = result.get("success", False)
    message = result.get("message", "")

    if not success and trx_id == -1:
        return ActionResult(outcome="failure", summary=message)

    # success=False with a valid trxId means SHA256 was already requested (dedup)
    label = "already tasked" if not success else "tasked successfully"
    return ActionResult(
        outcome="success",
        summary=f"File {label} (trxId: {trx_id})",
        format="markdown",
        output=f"**trxId:** `{trx_id}`\n\n{message}",
    )


def main():
    "Main executor"
    plugin.app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=False)  # noqa: S104


if __name__ == "__main__":
    main()
