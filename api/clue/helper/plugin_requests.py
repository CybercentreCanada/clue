from collections.abc import Callable
from time import monotonic
from typing import Any, TypeAlias
from urllib.parse import urljoin, urlsplit

from requests import Response
from requests.exceptions import ConnectionError, Timeout

_Timeout: TypeAlias = int | float | tuple[int | float | None, int | float | None] | None


def _timeout_budget(timeout: _Timeout) -> float | None:
    """Calculate the total duration represented by a requests timeout.

    Requests accepts either a scalar timeout or a (connect, read) pair. A
    timeout with an unbounded component has no finite total budget.

    Args:
        timeout: A numeric timeout, a connect/read timeout pair, or ``None``.

    Returns:
        The total timeout in seconds, or ``None`` when no finite budget exists.
    """
    if isinstance(timeout, tuple):
        # If either phase is unbounded, do not pretend the pair has a deadline.
        connect_timeout, read_timeout = timeout
        if connect_timeout is None or read_timeout is None:
            return None
        return float(connect_timeout) + float(read_timeout) or None
    return float(timeout) if timeout else None


def _remaining_timeout(timeout: _Timeout, remaining: float) -> _Timeout:
    """Fit an original timeout into the remaining overall request budget.

    Args:
        timeout: The original scalar or connect/read timeout setting.
        remaining: Time left before the overall deadline, in seconds.

    Returns:
        A timeout value that does not exceed the remaining budget. An
        unbounded setting is preserved as-is.
    """
    if isinstance(timeout, tuple):
        budget = _timeout_budget(timeout)
        if budget is None:
            return timeout
        # Preserve the connect/read ratio while shrinking both phases together.
        scale = min(1.0, remaining / budget)
        connect_timeout, read_timeout = timeout
        if connect_timeout is None or read_timeout is None:
            return timeout
        return float(connect_timeout) * scale, float(read_timeout) * scale
    if timeout is None:
        return None
    return min(float(timeout), remaining)


def _switch_to_get(status_code: int, get_method: Callable[..., Response] | None) -> bool:
    """Return whether a redirect should use the supplied GET method.

    Args:
        status_code: HTTP status code returned by the redirect response.
        get_method: Optional GET callable to use for method-changing redirects.

    Returns:
        Whether a GET method is available and the status commonly changes the
        redirected request to GET.
    """
    return get_method is not None and status_code in {301, 302, 303}


def _clear_request_body(kwargs: dict[str, Any]) -> None:
    """Remove payload and query arguments from a redirected GET request.

    Args:
        kwargs: Request keyword arguments, updated in place.
    """
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
    """Validate and prepare the next hop in a redirect chain.

    Args:
        response: The response that requested a redirect.
        url: The URL used for the current request.
        request_method: The method callable currently used for requests.
        get_method: Optional callable used when a redirect changes to GET.
        kwargs: Request keyword arguments, updated for the next hop.
        redirect_count: Number of redirects already followed.

    Returns:
        The request callable and absolute URL to use for the next hop. When a
        response has no Location header, the current method and URL are returned.

    Raises:
        ConnectionError: If the redirect target is invalid, unsafe, or exceeds
            the redirect limit.
    """
    location = response.headers.get("Location")
    if not location:
        return request_method, url

    try:
        # Resolve relative locations against the response URL, as HTTP requires.
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

    # Some redirect codes turn a request into GET; others retain its method.
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
    """Check whether a redirect stays on the same trusted host and port.

    Redirects are permitted within the same origin, and from the default HTTP
    origin to the default HTTPS origin on the same host. Other host, port,
    scheme, and embedded-credential changes are rejected.

    Args:
        current_url: URL from which the redirect originated.
        target_url: Resolved URL requested by the redirect response.

    Returns:
        Whether the redirect target satisfies the allowed origin rules.
    """
    try:
        current = urlsplit(current_url)
        target = urlsplit(target_url)
        # Reject non-web schemes, malformed hosts, and credential-bearing URLs.
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

    # Never let a plugin redirect send request headers to a different host.
    if current.hostname != target.hostname:
        return False
    # Permit same-origin redirects or only the conventional HTTP-to-HTTPS upgrade.
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
    """Send a request while safely following a bounded chain of redirects.

    Redirects are handled manually so each destination can be checked before
    sending the request again. A single total timeout budget is maintained
    across all hops when a finite timeout is supplied.

    Args:
        request_method: Callable used to send the initial request and redirects
            that preserve the method.
        url: Initial request URL.
        get_method: Optional callable to use when a redirect changes the method
            to GET.
        **kwargs: Additional keyword arguments passed to the request callable.
            ``allow_redirects`` is always disabled so this function can validate
            each redirect itself.

    Returns:
        The first response that does not request a redirect.

    Raises:
        ConnectionError: If a redirect is unsafe or the redirect limit is
            exceeded.
        Timeout: If the total timeout budget expires between redirect hops.
    """
    # Disable requests' automatic redirects to validate every target ourselves.
    kwargs["allow_redirects"] = False
    timeout = kwargs.get("timeout")
    budget = _timeout_budget(timeout)
    # Reuse one deadline so a chain cannot receive a fresh timeout per hop.
    deadline = monotonic() + budget if budget is not None else None

    for redirect_count in range(6):
        if deadline is not None and redirect_count > 0:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise Timeout("Plugin request exceeded its total timeout")
            # Pass only the time left to the next network operation.
            kwargs["timeout"] = _remaining_timeout(timeout, remaining)

        response = request_method(url, **kwargs)
        if response.status_code not in {301, 302, 303, 307, 308}:
            return response

        next_method, next_url = _next_redirect(response, url, request_method, get_method, kwargs, redirect_count)
        # A redirect status without Location is not actionable; return it intact.
        if next_url == url and not response.headers.get("Location"):
            return response
        request_method, url = next_method, next_url

    raise ConnectionError("Plugin exceeded the redirect limit")
