from collections.abc import Callable
from time import monotonic
from typing import Any
from urllib.parse import urljoin, urlsplit

from requests import Response
from requests.exceptions import ConnectionError, Timeout


def _timeout_budget(timeout: Any) -> float | None:
    if isinstance(timeout, tuple):
        if any(value is None for value in timeout):
            return None
        return sum(float(value) for value in timeout if value is not None) or None
    return float(timeout) if timeout else None


def _remaining_timeout(timeout: Any, remaining: float) -> Any:
    if isinstance(timeout, tuple):
        budget = _timeout_budget(timeout)
        if budget is None:
            return timeout
        scale = min(1.0, remaining / budget)
        return tuple(float(value) * scale for value in timeout)
    if timeout is None:
        return None
    return min(float(timeout), remaining)


def _switch_to_get(status_code: int, get_method: Callable[..., Response] | None) -> bool:
    return get_method is not None and status_code in {301, 302, 303}


def _clear_request_body(kwargs: dict[str, Any]) -> None:
    for key in ("json", "data", "files", "params"):
        kwargs.pop(key, None)


def _next_redirect(
    response: Response,
    url: str,
    request_method: Callable[..., Response],
    get_method: Callable[..., Response] | None,
    kwargs: dict[str, Any],
    redirect_count: int,
) -> tuple[Callable[..., Response], str]:
    location = response.headers.get("Location")
    if not location:
        return request_method, url

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

    switch_to_get = _switch_to_get(response.status_code, get_method)
    if switch_to_get:
        request_method = get_method  # type: ignore[assignment]
    if response.status_code == 303 or switch_to_get:
        _clear_request_body(kwargs)
    else:
        kwargs.pop("params", None)

    response.close()
    return request_method, target_url


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
    timeout = kwargs.get("timeout")
    budget = _timeout_budget(timeout)
    deadline = monotonic() + budget if budget is not None else None

    for redirect_count in range(6):
        if deadline is not None:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise Timeout("Plugin request exceeded its total timeout")
            kwargs["timeout"] = _remaining_timeout(timeout, remaining)

        response = request_method(url, **kwargs)
        if response.status_code not in {301, 302, 303, 307, 308}:
            return response

        next_method, next_url = _next_redirect(response, url, request_method, get_method, kwargs, redirect_count)
        if next_url == url and not response.headers.get("Location"):
            return response
        request_method, url = next_method, next_url

    raise ConnectionError("Plugin exceeded the redirect limit")
