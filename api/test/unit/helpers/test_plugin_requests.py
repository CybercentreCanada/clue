from unittest.mock import Mock

import pytest
from requests import Response
from requests.exceptions import ConnectionError, Timeout

from clue.common.exceptions import ClueValueError, NotFoundException
from clue.helper.plugin_requests import quote_plugin_path_segment, request_with_safe_redirects
from clue.models.validators import validate_plugin_identifier


@pytest.mark.parametrize(
    "value",
    [
        "",
        ".",
        "..",
        "../admin/keys",
        "x?role=admin",
        "../../etc/passwd",
        "../../../shutdown",
        "x#fragment",
        "%2e%2e%2fadmin",
        "x\\admin",
        ".x",
        "x.",
        "x..y",
        "x y",
        "x\n",
        "caf\u00e9",
    ],
)
def test_rejects_invalid_plugin_identifiers(value):
    with pytest.raises(ClueValueError) as error:
        validate_plugin_identifier(value)
    assert error.value.status_code == 400


@pytest.mark.parametrize("value", ["test_action-123", "ABC_09", "123", "a", "-", "_", "plugin.fetcher", "a.b.c"])
def test_accepts_safe_plugin_identifiers(value):
    assert validate_plugin_identifier(value) == value


@pytest.mark.parametrize(
    ("value", "encoded"),
    [
        ("../admin/keys", "%2E%2E%2Fadmin%2Fkeys"),
        ("x?role=admin", "x%3Frole%3Dadmin"),
        ("../../etc/passwd", "%2E%2E%2F%2E%2E%2Fetc%2Fpasswd"),
        ("../../../shutdown", "%2E%2E%2F%2E%2E%2F%2E%2E%2Fshutdown"),
        ("x#fragment", "x%23fragment"),
        ("%2e%2e%2fadmin", "%252e%252e%252fadmin"),
    ],
)
def test_path_segment_encoding_is_preserved(value, encoded):
    assert quote_plugin_path_segment(value) == encoded


@pytest.mark.parametrize("value", ["", ".", ".."])
def test_path_segment_encoding_rejects_standalone_dot_segments(value):
    with pytest.raises(NotFoundException):
        quote_plugin_path_segment(value)


def redirect(url: str, location: str, status_code: int = 308) -> Response:
    response = Response()
    response.status_code = status_code
    response.url = url
    response._content = b""
    response._content_consumed = True
    response.headers["Location"] = location
    return response


def success(url: str) -> Response:
    response = Response()
    response.status_code = 200
    response.url = url
    return response


@pytest.mark.parametrize(
    "destination",
    ["/lookup/", "https://plugin.example/lookup/"],
)
def test_follows_same_origin_redirects_and_https_upgrades(destination):
    start_url = "http://plugin.example/types/"
    response = redirect(start_url, destination)
    get = Mock(side_effect=[response, success("https://plugin.example/lookup/")])
    headers = {"Authorization": "Bearer secret", "X-Clue-Authorization": "clue-secret"}

    assert request_with_safe_redirects(get, start_url, headers=headers).status_code == 200
    assert get.call_count == 2
    assert get.call_args_list[0].kwargs["allow_redirects"] is False
    assert get.call_args_list[1].kwargs["headers"] == headers
    assert get.call_args_list[1].args[0] == (
        "http://plugin.example/lookup/" if destination.startswith("/") else destination
    )


def test_follows_redirect_on_same_custom_port():
    start_url = "http://plugin.example:8080/types/"
    get = Mock(side_effect=[redirect(start_url, "/canonical/types/"), success(start_url)])

    request_with_safe_redirects(get, start_url)

    assert get.call_args_list[1].args[0] == "http://plugin.example:8080/canonical/types/"


@pytest.mark.parametrize(
    "destination",
    [
        "https://other.example/lookup/",
        "http://plugin.example:8080/lookup/",
        "http://plugin.example:443/lookup/",
        "https://user:password@plugin.example/lookup/",
        "https://@plugin.example/lookup/",
        "http://plugin.example/lookup/",
    ],
)
def test_rejects_redirects_that_might_expose_credentials(destination):
    start_url = "https://plugin.example/types/"
    get = Mock(return_value=redirect(start_url, destination))

    with pytest.raises(ConnectionError, match="untrusted URL"):
        request_with_safe_redirects(get, start_url, headers={"Authorization": "Bearer secret"})

    get.assert_called_once()


def test_preserves_post_body_on_307_redirect():
    start_url = "http://plugin.example/lookup/"
    post = Mock(side_effect=[redirect(start_url, "/canonical/lookup/", 307), success(start_url)])

    request_with_safe_redirects(post, start_url, json=[{"value": "test"}])

    assert post.call_args_list[1].args[0] == "http://plugin.example/canonical/lookup/"
    assert post.call_args_list[1].kwargs["json"] == [{"value": "test"}]


def test_switches_post_to_get_on_302_redirect():
    start_url = "http://plugin.example/actions/run"
    post = Mock(return_value=redirect(start_url, "/actions/status", 302))
    get = Mock(return_value=success(start_url))

    request_with_safe_redirects(post, start_url, get_method=get, json={"run": True})

    get.assert_called_once_with("http://plugin.example/actions/status", allow_redirects=False)


def test_stops_after_five_redirects():
    start_url = "http://plugin.example/types/"
    get = Mock(side_effect=lambda url, **kwargs: redirect(url, "/types/"))

    with pytest.raises(ConnectionError, match="redirect limit"):
        request_with_safe_redirects(get, start_url)

    assert get.call_count == 6


def test_redirect_hops_share_a_total_timeout_budget(monkeypatch):
    now = [0.0]
    monkeypatch.setattr("clue.helper.plugin_requests.monotonic", lambda: now[0])
    start_url = "http://plugin.example/types/"

    def slow_redirect(url, **kwargs):
        now[0] += 0.6
        return redirect(url, "/types/")

    get = Mock(side_effect=slow_redirect)

    with pytest.raises(Timeout, match="total timeout"):
        request_with_safe_redirects(get, start_url, timeout=1.0)

    assert get.call_count == 2
    assert get.call_args_list[0].kwargs["timeout"] == 1.0
    assert get.call_args_list[1].kwargs["timeout"] == pytest.approx(0.4)


def test_redirect_hops_shrink_connect_and_read_timeouts_together(monkeypatch):
    now = [0.0]
    monkeypatch.setattr("clue.helper.plugin_requests.monotonic", lambda: now[0])
    start_url = "http://plugin.example/types/"

    def slow_redirect(url, **kwargs):
        now[0] += 4.0
        return redirect(url, "/types/")

    get = Mock(side_effect=slow_redirect)

    with pytest.raises(Timeout, match="total timeout"):
        request_with_safe_redirects(get, start_url, timeout=(2.0, 6.0))

    assert get.call_count == 2
    assert get.call_args_list[0].kwargs["timeout"] == (2.0, 6.0)
    assert get.call_args_list[1].kwargs["timeout"] == pytest.approx((1.0, 3.0))


def test_rejects_malformed_redirect_url():
    start_url = "https://plugin.example/types/"
    get = Mock(return_value=redirect(start_url, "https://[malformed/"))

    with pytest.raises(ConnectionError, match="untrusted URL"):
        request_with_safe_redirects(get, start_url)

    get.assert_called_once()
