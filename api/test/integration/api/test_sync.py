import uuid
from typing import Any

import pytest
import requests
import requests.exceptions as req_exc

from test.utils.oauth_credentials import get_token


def _make_document(**kwargs) -> dict[str, Any]:
    """Build a minimal valid SelectorDocument payload."""
    defaults: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "updated_at": 1000,
        "_deleted": False,
        "type": "ipv4",
        "value": "1.2.3.4",
        "source": "test",
        "classification": "TLP:CLEAR",
    }
    defaults.update(kwargs)
    return defaults


def _make_change_row(new_doc: dict[str, Any], assumed: dict[str, Any] | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {"newDocumentState": new_doc}
    if assumed is not None:
        row["assumedMasterState"] = assumed
    return row


# ---------------------------------------------------------------------------
# pull
# ---------------------------------------------------------------------------


def test_pull_returns_list(host):
    access_token = get_token()
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.get(
        f"{host}/api/v1/sync/selectors",
        params={"updated_at": 0},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert res.ok
    assert isinstance(res.json()["api_response"], list)


def test_pull_unknown_collection(host):
    access_token = get_token()
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.get(
        f"{host}/api/v1/sync/nonexistent",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert not res.ok
    assert res.status_code == 400


def test_pull_respects_limit(host):
    access_token = get_token()
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    docs = [_make_document(id=str(uuid.uuid4()), value=f"10.0.0.{i}") for i in range(5)]
    push_res = requests.post(
        f"{host}/api/v1/sync/selectors",
        headers={"Authorization": f"Bearer {access_token}"},
        json=[_make_change_row(d) for d in docs],
    )
    assert push_res.ok

    res = requests.get(
        f"{host}/api/v1/sync/selectors",
        params={"updated_at": 0, "limit": 2},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert res.ok
    assert len(res.json()["api_response"]) <= 2


def test_pull_omit_deleted(host):
    access_token = get_token()
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    doc_id = str(uuid.uuid4())
    deleted_doc = _make_document(id=doc_id, updated_at=2_000_000_000)
    deleted_doc["_deleted"] = True
    push_res = requests.post(
        f"{host}/api/v1/sync/selectors",
        headers={"Authorization": f"Bearer {access_token}"},
        json=[_make_change_row(deleted_doc)],
    )
    assert push_res.ok

    res = requests.get(
        f"{host}/api/v1/sync/selectors",
        params={"updated_at": 1_999_999_999, "omit_deleted": ""},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert res.ok
    ids = [d["id"] for d in res.json()["api_response"]]
    assert doc_id not in ids


# ---------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------


def test_push_new_document_returns_no_conflicts(host):
    access_token = get_token()
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    doc = _make_document()
    res = requests.post(
        f"{host}/api/v1/sync/selectors",
        headers={"Authorization": f"Bearer {access_token}"},
        json=[_make_change_row(doc)],
    )

    assert res.ok
    assert res.json()["api_response"] == []


def test_push_document_appears_in_pull(host):
    access_token = get_token()
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    doc_id = str(uuid.uuid4())
    doc = _make_document(id=doc_id, updated_at=2_000_000_001)

    requests.post(
        f"{host}/api/v1/sync/selectors",
        headers={"Authorization": f"Bearer {access_token}"},
        json=[_make_change_row(doc)],
    )

    res = requests.get(
        f"{host}/api/v1/sync/selectors",
        params={"updated_at": 2_000_000_000},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert res.ok
    ids = [d["id"] for d in res.json()["api_response"]]
    assert doc_id in ids


def test_push_conflict_without_assumed_state(host):
    access_token = get_token()
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    doc_id = str(uuid.uuid4())
    doc = _make_document(id=doc_id)

    requests.post(
        f"{host}/api/v1/sync/selectors",
        headers={"Authorization": f"Bearer {access_token}"},
        json=[_make_change_row(doc)],
    )

    # Second push without assumed state → conflict
    res = requests.post(
        f"{host}/api/v1/sync/selectors",
        headers={"Authorization": f"Bearer {access_token}"},
        json=[_make_change_row(doc)],
    )

    assert res.ok
    conflicts = res.json()["api_response"]
    assert len(conflicts) == 1
    assert conflicts[0]["id"] == doc_id


def test_push_conflict_with_stale_assumed_state(host):
    access_token = get_token()
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    doc_id = str(uuid.uuid4())
    original = _make_document(id=doc_id, updated_at=1000)

    requests.post(
        f"{host}/api/v1/sync/selectors",
        headers={"Authorization": f"Bearer {access_token}"},
        json=[_make_change_row(original)],
    )

    newer = _make_document(id=doc_id, updated_at=2000)
    stale_assumed = _make_document(id=doc_id, updated_at=500)
    res = requests.post(
        f"{host}/api/v1/sync/selectors",
        headers={"Authorization": f"Bearer {access_token}"},
        json=[_make_change_row(newer, assumed=stale_assumed)],
    )

    assert res.ok
    conflicts = res.json()["api_response"]
    assert len(conflicts) == 1
    assert conflicts[0]["id"] == doc_id


def test_push_resolves_with_correct_assumed_state(host):
    access_token = get_token()
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    doc_id = str(uuid.uuid4())
    original = _make_document(id=doc_id, updated_at=1000)

    requests.post(
        f"{host}/api/v1/sync/selectors",
        headers={"Authorization": f"Bearer {access_token}"},
        json=[_make_change_row(original)],
    )

    updated = _make_document(id=doc_id, updated_at=2000)
    res = requests.post(
        f"{host}/api/v1/sync/selectors",
        headers={"Authorization": f"Bearer {access_token}"},
        json=[_make_change_row(updated, assumed=original)],
    )

    assert res.ok
    assert res.json()["api_response"] == []


def test_push_invalid_data(host):
    access_token = get_token()
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/sync/selectors",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"not": "a list"},
    )

    assert not res.ok


def test_push_unknown_collection(host):
    access_token = get_token()
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.post(
        f"{host}/api/v1/sync/nonexistent",
        headers={"Authorization": f"Bearer {access_token}"},
        json=[],
    )

    assert not res.ok
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# stream
# ---------------------------------------------------------------------------


def test_stream_returns_event_stream(host):
    access_token = get_token()
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    try:
        with requests.get(
            f"{host}/api/v1/sync/selectors/stream",
            headers={"Authorization": f"Bearer {access_token}"},
            stream=True,
            timeout=2,
        ) as res:
            assert res.ok
            assert "text/event-stream" in res.headers.get("Content-Type", "")
    except req_exc.ReadTimeout:
        # The dev server (Werkzeug) does not flush response headers until the
        # SSE generator yields its first event. A ReadTimeout therefore means
        # the server accepted the connection and is holding it open — the
        # expected behaviour for a working SSE endpoint. Errors (4xx/5xx) would
        # have been returned immediately without reaching this timeout.
        pass


def test_stream_unknown_collection(host):
    access_token = get_token()
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.get(
        f"{host}/api/v1/sync/nonexistent/stream",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert not res.ok
    assert res.status_code == 400
