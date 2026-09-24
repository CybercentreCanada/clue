from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin, urlsplit

from requests import Response
from requests.exceptions import ConnectionError


def _safe_redirect(current_url: str, target_url: str) -> bool:
    """Allow redirects within an origin, or an upgrade from HTTP to HTTPS on the same host."""
    try:
        current = urlsplit(current_url)
        target = urlsplit(target_url)
        if (
            target.scheme not in {"http", "https"}
            or not target.hostname
            or target.username is not None
            or target.password is not None
        ):
            return False
        current_port = current.port or (443 if current.scheme == "https" else 80)
        target_port = target.port or (443 if target.scheme == "https" else 80)
    except ValueError:
        return False

    if current.hostname != target.hostname:
        return False
    if current.scheme == target.scheme and current_port == target_port:
        return True
    return current.scheme == "http" and current_port == 80 and target.scheme == "https" and target_port == 443


def request_with_safe_redirects(
    request_method: Callable[..., Response],
    url: str,
    *,
    get_method: Callable[..., Response] | None = None,
    **kwargs: Any,
) -> Response:
    """Follow bounded plugin redirects without forwarding credentials to another origin."""
    kwargs["allow_redirects"] = False
    for redirect_count in range(6):
        response = request_method(url, **kwargs)
        if response.status_code not in {301, 302, 303, 307, 308}:
            return response

        location = response.headers.get("Location")
        if not location:
            return response
        try:
            target_url = urljoin(response.url or url, location)
        except ValueError as err:
            response.close()
            raise ConnectionError("Plugin redirected to an untrusted URL") from err
        if not _safe_redirect(url, target_url):
            response.close()
            raise ConnectionError("Plugin redirected to an untrusted URL")
        if redirect_count == 5:
            response.close()
            raise ConnectionError("Plugin exceeded the redirect limit")

        if response.status_code == 303 or (response.status_code in {301, 302} and get_method is not None):
            if get_method is not None:
                request_method = get_method
            for key in ("json", "data", "files"):
                kwargs.pop(key, None)

        kwargs.pop("params", None)
        response.close()
        url = target_url

    raise ConnectionError("Plugin exceeded the redirect limit")
