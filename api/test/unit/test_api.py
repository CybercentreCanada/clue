import io

import pytest
from flask import Blueprint, Flask
from pydantic import BaseModel

import clue.api as api


@pytest.fixture(scope="module")
def app():
    flask_app = Flask("test_api")
    flask_app.config["SECRET_KEY"] = "testing"
    return flask_app


class _SampleModel(BaseModel):
    name: str
    value: int


# ---------------------------------------------------------------------------
# make_subapi_blueprint
# ---------------------------------------------------------------------------


class TestMakeSubapiBlueprint:
    def test_returns_blueprint(self):
        bp = api.make_subapi_blueprint("widgets")
        assert isinstance(bp, Blueprint)

    def test_default_version_prefix(self):
        bp = api.make_subapi_blueprint("widgets")
        assert bp.url_prefix == "/api/v1/widgets"

    def test_custom_version_prefix(self):
        bp = api.make_subapi_blueprint("things", api_version=3)
        assert bp.url_prefix == "/api/v3/things"

    def test_blueprint_name(self):
        bp = api.make_subapi_blueprint("my_service")
        assert bp.name == "my_service"


# ---------------------------------------------------------------------------
# _make_api_response (exercised via public helpers)
# ---------------------------------------------------------------------------


class TestMakeApiResponse:
    @pytest.fixture(autouse=True)
    def ctx(self, app):
        with app.test_request_context():
            yield

    def test_content_type_is_json(self):
        resp = api.ok()
        assert resp.content_type == "application/json"

    def test_envelope_contains_api_response_key(self):
        resp = api.ok({"key": "val"})
        assert "api_response" in resp.json

    def test_envelope_contains_status_code(self):
        resp = api.ok()
        assert resp.json["api_status_code"] == 200

    def test_envelope_contains_server_version(self):
        resp = api.ok()
        assert "api_server_version" in resp.json

    def test_envelope_omits_error_when_none(self):
        # error_message defaults to "" (empty string), not None, so it is
        # serialized. Verify it is present but empty.
        resp = api.ok()
        assert resp.json.get("api_error_message", None) == ""

    def test_envelope_includes_error_string(self):
        resp = api.bad_request(err="Something bad")
        assert resp.json["api_error_message"] == "Something bad"

    def test_warnings_are_included(self):
        resp = api.created(warnings=["heads up"])
        assert resp.json["api_warning"] == ["heads up"]

    def test_custom_dict_data(self):
        resp = api.ok({"items": [1, 2, 3]})
        assert resp.json["api_response"] == {"items": [1, 2, 3]}

    def test_basemodel_data_is_serialized(self):
        model = _SampleModel(name="foo", value=42)
        resp = api.ok(model)
        assert resp.json["api_response"] == {"name": "foo", "value": 42}

    def test_list_of_basemodel_is_serialized(self):
        models = [_SampleModel(name="a", value=1), _SampleModel(name="b", value=2)]
        resp = api.ok(models)
        assert resp.json["api_response"] == [
            {"name": "a", "value": 1},
            {"name": "b", "value": 2},
        ]

    def test_cookie_is_set_on_response(self):
        resp = api.ok(cookies={"session": "abc123"})
        assert "session=abc123" in resp.headers.get("Set-Cookie", "")

    def test_multiple_cookies_are_set(self):
        resp = api.ok(cookies={"a": "1", "b": "2"})
        cookie_keys = {c.split("=")[0] for c in resp.headers.getlist("Set-Cookie")}
        assert {"a", "b"} <= cookie_keys

    def test_non_dict_cookies_are_ignored(self):
        # cookies not a dict → no cookies set, no exception raised
        resp = api.ok(cookies=None)
        assert resp.status_code == 200

    def test_exception_err_produces_class_name_in_message(self):
        exc = ValueError("test error")
        resp = api.bad_request(err=exc)  # type: ignore[arg-type]
        assert "ValueError" in resp.json["api_error_message"]

    def test_exception_err_produces_message_text(self):
        exc = RuntimeError("runtime problem")
        resp = api.bad_request(err=exc)  # type: ignore[arg-type]
        assert "runtime problem" in resp.json["api_error_message"]


# ---------------------------------------------------------------------------
# Status-code helpers
# ---------------------------------------------------------------------------


class TestStatusCodeHelpers:
    @pytest.fixture(autouse=True)
    def ctx(self, app):
        with app.test_request_context():
            yield

    @pytest.mark.parametrize(
        "helper,expected_status,default_success",
        [
            (api.ok, 200, True),
            (api.created, 201, True),
            (api.accepted, 202, True),
            (api.no_content, 204, True),
            (api.not_modified, 304, True),
            (api.bad_request, 400, False),
            (api.unauthorized, 401, False),
            (api.forbidden, 403, False),
            (api.not_found, 404, False),
            (api.conflict, 409, False),
            (api.precondition_failed, 412, False),
            (api.too_many_requests, 429, False),
            (api.internal_error, 500, False),
            (api.not_implemented, 501, False),
            (api.bad_gateway, 502, False),
            (api.service_unavailable, 503, False),
        ],
    )
    def test_status_code_and_default_success(self, helper, expected_status, default_success):
        resp = helper()
        assert resp.status_code == expected_status
        assert resp.json["api_response"]["success"] is default_success

    def test_teapot_status_code(self):
        resp = api.teapot()
        assert resp.status_code == 418

    def test_teapot_default_data(self):
        resp = api.teapot()
        assert resp.json["api_response"] == {"success": False, "teapot": True}

    def test_bad_request_accepts_warnings(self):
        resp = api.bad_request(warnings=["watch out"])
        assert resp.json["api_warning"] == ["watch out"]


# ---------------------------------------------------------------------------
# make_file_response
# ---------------------------------------------------------------------------


class TestMakeFileResponse:
    @pytest.fixture(autouse=True)
    def ctx(self, app):
        with app.test_request_context():
            yield

    def test_default_status_code(self):
        resp = api.make_file_response(b"data", "file.bin", 4)
        assert resp.status_code == 200

    def test_custom_status_code(self):
        resp = api.make_file_response(b"data", "file.bin", 4, status_code=206)
        assert resp.status_code == 206

    def test_default_content_type(self):
        resp = api.make_file_response(b"data", "file.bin", 4)
        assert resp.headers["Content-Type"] == "application/octet-stream"

    def test_custom_content_type(self):
        resp = api.make_file_response(b"data", "report.pdf", 4, content_type="application/pdf")
        assert resp.headers["Content-Type"] == "application/pdf"

    def test_content_length_header(self):
        resp = api.make_file_response(b"data", "file.bin", 99)
        assert resp.headers["Content-Length"] == "99"

    def test_content_disposition_contains_filename(self):
        resp = api.make_file_response(b"data", "my_file.txt", 4)
        assert 'filename="my_file.txt"' in resp.headers["Content-Disposition"]

    def test_response_body(self):
        resp = api.make_file_response(b"hello", "f.bin", 5)
        assert resp.data == b"hello"


# ---------------------------------------------------------------------------
# stream_file_response
# ---------------------------------------------------------------------------


class TestStreamFileResponse:
    @pytest.fixture(autouse=True)
    def ctx(self, app):
        with app.test_request_context():
            yield

    def test_default_status_code(self):
        resp = api.stream_file_response(io.BytesIO(b"abc"), "f.bin", 3)
        assert resp.status_code == 200

    def test_custom_status_code(self):
        resp = api.stream_file_response(io.BytesIO(b"abc"), "f.bin", 3, status_code=206)
        assert resp.status_code == 206

    def test_content_type(self):
        resp = api.stream_file_response(io.BytesIO(b"abc"), "f.bin", 3)
        assert resp.headers["Content-Type"] == "application/octet-stream"

    def test_content_length_header(self):
        resp = api.stream_file_response(io.BytesIO(b"abc"), "f.bin", 42)
        assert resp.headers["Content-Length"] == "42"

    def test_content_disposition_contains_filename(self):
        resp = api.stream_file_response(io.BytesIO(b"abc"), "archive.zip", 3)
        assert 'filename="archive.zip"' in resp.headers["Content-Disposition"]

    def test_streaming_yields_all_data(self):
        data = b"chunk1chunk2"
        resp = api.stream_file_response(io.BytesIO(data), "f.bin", len(data))
        assert b"".join(resp.response) == data


# ---------------------------------------------------------------------------
# make_binary_response
# ---------------------------------------------------------------------------


class TestMakeBinaryResponse:
    @pytest.fixture(autouse=True)
    def ctx(self, app):
        with app.test_request_context():
            yield

    def test_default_status_code(self):
        resp = api.make_binary_response(b"bytes", 5)
        assert resp.status_code == 200

    def test_custom_status_code(self):
        resp = api.make_binary_response(b"bytes", 5, status_code=201)
        assert resp.status_code == 201

    def test_content_type(self):
        resp = api.make_binary_response(b"bytes", 5)
        assert resp.headers["Content-Type"] == "application/octet-stream"

    def test_content_length_header(self):
        resp = api.make_binary_response(b"bytes", 100)
        assert resp.headers["Content-Length"] == "100"

    def test_response_body(self):
        resp = api.make_binary_response(b"raw data", 8)
        assert resp.data == b"raw data"


# ---------------------------------------------------------------------------
# stream_binary_response
# ---------------------------------------------------------------------------


class TestStreamBinaryResponse:
    @pytest.fixture(autouse=True)
    def ctx(self, app):
        with app.test_request_context():
            yield

    def test_default_status_code(self):
        resp = api.stream_binary_response(io.BytesIO(b"data"))
        assert resp.status_code == 200

    def test_custom_status_code(self):
        resp = api.stream_binary_response(io.BytesIO(b"data"), status_code=202)
        assert resp.status_code == 202

    def test_mimetype(self):
        resp = api.stream_binary_response(io.BytesIO(b"data"))
        assert resp.content_type == "application/octet-stream"

    def test_streaming_yields_all_data(self):
        data = b"binary content here"
        resp = api.stream_binary_response(io.BytesIO(data))
        assert b"".join(resp.response) == data
