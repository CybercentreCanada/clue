from typing import Literal

import requests
from clue.common.exceptions import AuthenticationException, ClueException, TimeoutException, UnprocessableException
from consts import MISP_API_KEY, MISP_URL, VERIFY

# Reuse TCP connections across requests, MISP returns 500 if too many connections
_session = requests.Session()
_session.headers.update(
    {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": MISP_API_KEY,
    }
)


def misp_request(method: Literal["get", "post"], path: str, timeout: float, **kwargs) -> dict | list:
    """Submit a request to MISP.

    Submits an HTTP request to MISP. Creates a requests.Session at module init
    and reuses for all subsequent requests.

    Args:
        method: Verb for http request
        path: URL path, appended to MISP_URL
        timeout: Request timeout
        kwargs: Any additional parameters to pass into the request

    Returns:
        MISP's JSON API response to the request

    Raises:
        UnprocessableException: If no API key is configured
        TimeoutException: If MISP does not respond with timeout
        AuthenticationException: If MISP rejects the API key or the API user is missing permissions
        ClueException: If the connection fails, MISP returns an error status or the body is not JSON
    """
    if not MISP_API_KEY:
        raise UnprocessableException("No API key is provided. An API key is required")

    try:
        rsp = _session.request(method, f"{MISP_URL}{path}", verify=VERIFY, timeout=timeout, **kwargs)
    except requests.exceptions.Timeout as e:
        raise TimeoutException("MISP failed to respond in time", cause=e)
    except requests.exceptions.ConnectionError as e:
        raise ClueException(f"Failed to connect to MISP: {e}", cause=e)
    except requests.exceptions.RequestException as e:
        raise ClueException(f"Request failed: {e}", cause=e)

    try:
        rsp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        try:
            msg = rsp.json().get("message") or rsp.text[:200]
        except (ValueError, AttributeError):
            msg = rsp.text[:200]

        if rsp.status_code == 403:
            raise AuthenticationException(f"MISP rejected the request [{MISP_URL}]: {msg}", cause=e)

        raise ClueException(f"Error requesting data [{rsp.status_code}]: {msg}", cause=e)

    try:
        return rsp.json()
    except ValueError as e:
        raise ClueException(f"MISP returned non JSON response: {rsp.text[:200]}", cause=e)
