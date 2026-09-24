from unittest.mock import Mock

import pytest
from requests import Response
from requests.exceptions import ConnectionError

from clue.helper.plugin_requests import request_with_safe_redirects


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


def test_rejects_malformed_redirect_url():
    start_url = "https://plugin.example/types/"
    get = Mock(return_value=redirect(start_url, "https://[malformed/"))

    with pytest.raises(ConnectionError, match="untrusted URL"):
        request_with_safe_redirects(get, start_url)

    get.assert_called_once()
