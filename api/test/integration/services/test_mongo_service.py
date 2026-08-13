"""Integration tests for clue.services.mongo_service.

These tests run against real MongoDB and Redis instances (via the dev docker-compose
stack). Tests are automatically skipped when those services are unavailable.
"""

import json
import threading
import time
import uuid
from unittest.mock import MagicMock, patch

import pytest
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

import clue.services.mongo_service as mongo_service
from clue.common.exceptions import ClueRuntimeError, ClueValueError
from clue.config import config, get_redis
from clue.models.config import ExternalSource
from clue.models.selector import Selector
from clue.models.sync import ChangeRow, SelectorDocument

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_doc(**kwargs) -> SelectorDocument:
    defaults: dict = {"type": "ipv4", "value": "1.2.3.4", "source": "test"}
    defaults.update(kwargs)
    return SelectorDocument(**defaults)


def _make_row(new_doc: SelectorDocument | None = None, assumed: SelectorDocument | None = None) -> ChangeRow:
    return ChangeRow.model_construct(
        new_document_state=new_doc or _make_doc(),
        assumed_master_state=assumed,
    )


# ---------------------------------------------------------------------------
# Session-scoped connectivity fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mongo_client():
    """Real MongoClient. Skips the entire session if MongoDB is unavailable."""
    try:
        client = MongoClient(
            config.core.mongodb.host,
            config.core.mongodb.port,
            serverSelectionTimeoutMS=3000,
        )
        client.admin.command("ping")
        yield client
    except Exception:
        pytest.skip("MongoDB is not available for integration tests.")


@pytest.fixture(scope="session")
def live_redis():
    """Real Redis client. Skips if unavailable."""
    try:
        r = get_redis()
        r.ping()
        return r
    except Exception:
        pytest.skip("Redis is not available for integration tests.")


# ---------------------------------------------------------------------------
# Per-test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_user(mongo_client):
    """Unique per-test username with automatic MongoDB collection cleanup."""
    user = f"test_{uuid.uuid4().hex}"
    yield user
    db = mongo_client[config.core.mongodb.database]
    for name in list(db.list_collection_names()):
        if name.startswith(f"{user}-"):
            db.drop_collection(name)
    mongo_service.INITIALIZED_COLLECTIONS.discard(f"{user}-selectors")


@pytest.fixture(autouse=True)
def reset_mongo_client():
    """Save and restore MONGO_CLIENT around each test."""
    original = mongo_service.MONGO_CLIENT
    yield
    mongo_service.MONGO_CLIENT = original


# ---------------------------------------------------------------------------
# _get_event_id
# ---------------------------------------------------------------------------


class TestGetEventId:
    def test_returns_integer(self, live_redis):
        result = mongo_service._get_event_id()
        assert isinstance(result, int)

    def test_increments_on_each_call(self, live_redis):
        a = mongo_service._get_event_id()
        b = mongo_service._get_event_id()
        c = mongo_service._get_event_id()
        assert b == a + 1
        assert c == b + 1


# ---------------------------------------------------------------------------
# _connect
# ---------------------------------------------------------------------------


class TestConnect:
    def test_connects_and_returns_live_client(self, mongo_client):
        mongo_service.MONGO_CLIENT = None
        client = mongo_service._connect()
        client.admin.command("ping")  # verifies the connection is live

    def test_reuses_existing_healthy_client(self, mongo_client):
        mongo_service.MONGO_CLIENT = None
        first = mongo_service._connect()
        second = mongo_service._connect()
        assert first is second

    def test_raises_after_all_retries_when_host_is_unreachable(self):
        mongo_service.MONGO_CLIENT = None
        # Patch only the config values that control the connection target/retries.
        with (
            patch.object(config.core.mongodb, "host", "192.0.2.1"),  # TEST-NET, guaranteed unreachable
            patch.object(config.core.mongodb, "max_retries", 0),
            patch.object(config.core.mongodb, "connect_timeout", 100),
            patch.object(config.core.mongodb, "server_selection_timeout", 100),
        ):
            with pytest.raises(ClueRuntimeError, match="Failed to connect to MongoDB") as exc_info:
                mongo_service._connect()

        assert isinstance(exc_info.value.__cause__, ConnectionFailure)


# ---------------------------------------------------------------------------
# _get_collection
# ---------------------------------------------------------------------------


class TestGetCollection:
    def test_raises_for_unknown_collection(self):
        with pytest.raises(ClueValueError, match="Unknown collection"):
            mongo_service._get_collection("user1", "not_a_real_collection")

    def test_raises_when_no_mongodb_host_configured(self):
        with patch.object(config.core.mongodb, "host", ""):
            with pytest.raises(ClueRuntimeError, match="No mongodb host"):
                mongo_service._get_collection("user1", "selectors")

    def test_creates_collection_with_indexes_on_first_call(self, test_user, mongo_client):
        col = mongo_service._get_collection(test_user, "selectors")
        db = mongo_client[config.core.mongodb.database]
        assert f"{test_user}-selectors" in db.list_collection_names()
        index_names = list(col.index_information().keys())
        assert any("updated_at" in n for n in index_names)

    def test_adds_collection_to_initialized_set(self, test_user):
        mongo_service._get_collection(test_user, "selectors")
        assert f"{test_user}-selectors" in mongo_service.INITIALIZED_COLLECTIONS

    def test_returns_collection_with_expected_name(self, test_user):
        col = mongo_service._get_collection(test_user, "selectors")
        assert col.name == f"{test_user}-selectors"

    def test_skips_recreation_for_already_initialized_collection(self, test_user, mongo_client):
        mongo_service._get_collection(test_user, "selectors")
        db = mongo_client[config.core.mongodb.database]
        names_before = set(db.list_collection_names())
        mongo_service._get_collection(test_user, "selectors")
        names_after = set(db.list_collection_names())
        assert names_before == names_after


# ---------------------------------------------------------------------------
# build_pubsub
# ---------------------------------------------------------------------------


class TestBuildPubsub:
    def test_returns_usable_pubsub(self, live_redis):
        pubsub = mongo_service.build_pubsub()
        try:
            pubsub.subscribe("test-channel")
            assert len(pubsub.channels) == 1
        finally:
            pubsub.close()


# ---------------------------------------------------------------------------
# event_stream
# ---------------------------------------------------------------------------


class TestEventStream:
    def test_raises_for_unknown_collection(self):
        with pytest.raises(ClueValueError, match="Unknown collection"):
            mongo_service.event_stream("user1", "not_a_collection")

    def test_returns_text_event_stream_response(self, live_redis):
        user = f"test_{uuid.uuid4().hex}"
        response = mongo_service.event_stream(user, "selectors")
        response.response.close()
        assert response.content_type.startswith("text/event-stream")

    def test_subscribes_to_correct_channel(self, live_redis):
        user = f"test_{uuid.uuid4().hex}"
        # Capture the real pubsub created internally so we can inspect it.
        captured: list = []
        original_build = mongo_service.build_pubsub

        def capturing():
            ps = original_build()
            captured.append(ps)
            return ps

        with patch("clue.services.mongo_service.build_pubsub", side_effect=capturing):
            response = mongo_service.event_stream(user, "selectors")

        assert len(captured) == 1
        assert f"{user}-selectors".encode() in captured[0].channels
        response.response.close()

    def test_streams_published_message_as_json_event(self, live_redis):
        user = f"test_{uuid.uuid4().hex}"
        payload = {"documents": [], "checkpoint": None}

        # event_stream subscribes synchronously before returning, so publishing
        # after the call but before consuming the generator is safe.
        response = mongo_service.event_stream(user, "selectors")
        gen = response.response

        def delayed_publish():
            time.sleep(0.1)
            live_redis.publish(f"{user}-selectors", json.dumps(payload))

        t = threading.Thread(target=delayed_publish, daemon=True)
        t.start()

        # next(gen) blocks until the message arrives; the subscribe confirmation
        # is filtered out internally, so the first yielded chunk is our message.
        chunk = next(gen)
        gen.close()  # triggers finally: pubsub.close()
        t.join()

        event = json.loads(chunk)
        assert "id" in event
        assert "documents" in event

    def test_closes_pubsub_on_generator_close(self, live_redis):
        user = f"test_{uuid.uuid4().hex}"
        payload = {"documents": [], "checkpoint": None}
        captured: list = []
        original_build = mongo_service.build_pubsub

        def capturing():
            ps = original_build()
            captured.append(ps)
            return ps

        with patch("clue.services.mongo_service.build_pubsub", side_effect=capturing):
            response = mongo_service.event_stream(user, "selectors")
            gen = response.response

            def delayed_publish():
                time.sleep(0.1)
                live_redis.publish(f"{user}-selectors", json.dumps(payload))

            t = threading.Thread(target=delayed_publish, daemon=True)
            t.start()
            next(gen)
            gen.close()
            t.join()

        # After close(), the pubsub connection is released back to the pool.
        assert captured[0].connection is None


# ---------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------


class TestPush:
    def test_inserts_new_document_returns_no_conflicts(self, test_user, live_redis):
        doc = _make_doc()
        conflicts = mongo_service.push(test_user, "selectors", [_make_row(new_doc=doc)])
        assert conflicts == []
        results = mongo_service.pull(test_user, "selectors", id=None, updated_at=0, batch_size=100)
        assert any(r.id == doc.id for r in results)

    def test_conflict_when_record_exists_without_assumed_state(self, test_user, live_redis):
        doc = _make_doc(id="conflict-id")
        mongo_service.push(test_user, "selectors", [_make_row(new_doc=doc)])
        conflicts = mongo_service.push(test_user, "selectors", [_make_row(new_doc=doc, assumed=None)])
        assert len(conflicts) == 1
        assert conflicts[0].id == "conflict-id"

    def test_conflict_when_assumed_state_is_stale(self, test_user, live_redis):
        existing = _make_doc(id="stale-id", updated_at=1000)
        mongo_service.push(test_user, "selectors", [_make_row(new_doc=existing)])

        newer = _make_doc(id="stale-id", updated_at=2000)
        stale_assumed = _make_doc(id="stale-id", updated_at=999)
        conflicts = mongo_service.push(test_user, "selectors", [_make_row(new_doc=newer, assumed=stale_assumed)])
        assert len(conflicts) == 1

    def test_updates_document_when_assumed_state_matches(self, test_user, live_redis):
        doc = _make_doc(id="update-id", updated_at=100)
        mongo_service.push(test_user, "selectors", [_make_row(new_doc=doc)])

        updated = _make_doc(id="update-id", updated_at=200)
        correct_assumed = _make_doc(id="update-id", updated_at=100)
        conflicts = mongo_service.push(test_user, "selectors", [_make_row(new_doc=updated, assumed=correct_assumed)])

        assert conflicts == []
        results = mongo_service.pull(test_user, "selectors", id=None, updated_at=0, batch_size=100)
        record = next(r for r in results if r.id == "update-id")
        assert record.updated_at == 200

    def test_publishes_redis_event_on_successful_write(self, test_user, live_redis):
        pubsub = live_redis.pubsub()
        pubsub.subscribe(f"{test_user}-selectors")
        time.sleep(0.05)  # let subscription register

        doc = _make_doc()
        mongo_service.push(test_user, "selectors", [_make_row(new_doc=doc)])

        received = None
        for _ in range(20):
            msg = pubsub.get_message(timeout=0.1)
            if msg and msg["type"] == "message":
                received = msg
                break
        pubsub.close()

        assert received is not None
        event_data = json.loads(received["data"])
        assert "documents" in event_data

    def test_no_publish_when_all_rows_are_conflicts(self, test_user, live_redis):
        doc = _make_doc(id="no-pub-id")
        mongo_service.push(test_user, "selectors", [_make_row(new_doc=doc)])

        pubsub = live_redis.pubsub()
        pubsub.subscribe(f"{test_user}-selectors")
        time.sleep(0.05)

        conflicts = mongo_service.push(test_user, "selectors", [_make_row(new_doc=doc, assumed=None)])
        # Give any potential publish time to arrive
        time.sleep(0.1)
        msg = pubsub.get_message()
        pubsub.close()

        assert len(conflicts) == 1
        # The only message in the buffer should be the subscribe confirmation, not a data event
        assert msg is None or msg["type"] != "message"

    def test_reraises_on_mid_transaction_exception(self, test_user, live_redis):
        # Pre-initialize the collection so _get_collection returns the same object.
        col = mongo_service._get_collection(test_user, "selectors")
        real_find_one = col.find_one

        def failing_find_one(*args, **kwargs):
            raise RuntimeError("injected db failure")

        col.find_one = failing_find_one
        try:
            with (
                patch("clue.services.mongo_service._get_collection", return_value=col),
                pytest.raises(RuntimeError, match="injected db failure"),
            ):
                mongo_service.push(test_user, "selectors", [_make_row()])
        finally:
            col.find_one = real_find_one

    def test_returns_empty_for_empty_input(self, test_user, live_redis):
        conflicts = mongo_service.push(test_user, "selectors", [])
        assert conflicts == []


# ---------------------------------------------------------------------------
# pull
# ---------------------------------------------------------------------------


class TestPull:
    def test_returns_pushed_documents(self, test_user, live_redis):
        doc = _make_doc(value="9.9.9.9")
        mongo_service.push(test_user, "selectors", [_make_row(new_doc=doc)])
        results = mongo_service.pull(test_user, "selectors", id=None, updated_at=0, batch_size=100)
        assert any(r.id == doc.id for r in results)
        assert all(isinstance(r, SelectorDocument) for r in results)

    def test_respects_batch_size(self, test_user, live_redis):
        docs = [_make_doc(id=str(uuid.uuid4()), value=f"10.0.0.{i}") for i in range(5)]
        mongo_service.push(test_user, "selectors", [_make_row(new_doc=d) for d in docs])
        results = mongo_service.pull(test_user, "selectors", id=None, updated_at=0, batch_size=2)
        assert len(results) <= 2

    def test_omit_deleted_excludes_soft_deleted_docs(self, test_user, live_redis):
        live_doc = _make_doc(id="live")
        dead_doc = _make_doc(id="dead", deleted=True)
        mongo_service.push(test_user, "selectors", [_make_row(new_doc=live_doc), _make_row(new_doc=dead_doc)])

        results = mongo_service.pull(test_user, "selectors", id=None, updated_at=0, batch_size=100, omit_deleted=True)
        ids = [r.id for r in results]
        assert "live" in ids
        assert "dead" not in ids

    def test_includes_deleted_docs_by_default(self, test_user, live_redis):
        dead_doc = _make_doc(id="deleted-doc", deleted=True)
        mongo_service.push(test_user, "selectors", [_make_row(new_doc=dead_doc)])
        results = mongo_service.pull(test_user, "selectors", id=None, updated_at=0, batch_size=100)
        assert any(r.id == "deleted-doc" for r in results)

    def test_returns_empty_list_when_no_documents(self, test_user, live_redis):
        # Fresh test_user has no documents
        results = mongo_service.pull(test_user, "selectors", id=None, updated_at=0, batch_size=10)
        assert results == []

    def test_checkpoint_filters_older_documents(self, test_user, live_redis):
        old = _make_doc(id="old-doc", updated_at=100)
        new = _make_doc(id="new-doc", updated_at=9_999_999_999)
        mongo_service.push(test_user, "selectors", [_make_row(new_doc=old), _make_row(new_doc=new)])

        results = mongo_service.pull(test_user, "selectors", id=None, updated_at=1_000_000_000, batch_size=100)
        ids = [r.id for r in results]
        assert "new-doc" in ids
        assert "old-doc" not in ids


# ---------------------------------------------------------------------------
# existing_results
# ---------------------------------------------------------------------------


class TestExistingResults:
    def test_returns_empty_dict_when_replication_disabled(self):
        with patch.object(config.ui, "replication", False):
            result = mongo_service.existing_results("user1", "selectors", [], [])
        assert result == {}

    def test_returns_matching_docs_grouped_by_source(self, test_user, live_redis):
        doc = _make_doc(id="er-doc", source="plugin_a")
        mongo_service.push(test_user, "selectors", [_make_row(new_doc=doc)])

        source = ExternalSource(name="plugin_a", url="http://plugin_a/")
        selectors = [Selector(type="ipv4", value="1.2.3.4")]

        with patch.object(config.ui, "replication", True):
            result = mongo_service.existing_results(test_user, "selectors", selectors, [source])

        assert "plugin_a" in result
        assert any(r["value"] == "1.2.3.4" for r in result["plugin_a"])

    def test_excludes_deleted_documents(self, test_user, live_redis):
        doc = _make_doc(id="del-er-doc", source="plugin_b", deleted=True)
        mongo_service.push(test_user, "selectors", [_make_row(new_doc=doc)])

        source = ExternalSource(name="plugin_b", url="http://plugin_b/")
        selectors = [Selector(type="ipv4", value="1.2.3.4")]

        with patch.object(config.ui, "replication", True):
            result = mongo_service.existing_results(test_user, "selectors", selectors, [source])

        assert "plugin_b" not in result

    def test_excludes_docs_with_errors(self, test_user, live_redis):
        doc = _make_doc(id="err-er-doc", source="plugin_c", error="something failed")
        mongo_service.push(test_user, "selectors", [_make_row(new_doc=doc)])

        source = ExternalSource(name="plugin_c", url="http://plugin_c/")
        selectors = [Selector(type="ipv4", value="1.2.3.4")]

        with patch.object(config.ui, "replication", True):
            result = mongo_service.existing_results(test_user, "selectors", selectors, [source])

        assert "plugin_c" not in result

    def test_returns_empty_dict_on_clue_runtime_error(self):
        selectors = [Selector(type="ipv4", value="1.2.3.4")]
        with (
            patch("clue.services.mongo_service._get_collection", side_effect=ClueRuntimeError("no db")),
            patch.object(config.ui, "replication", True),
        ):
            result = mongo_service.existing_results("user1", "selectors", selectors, [])
        assert result == {}


# ---------------------------------------------------------------------------
# invalidate_existing
# ---------------------------------------------------------------------------


class TestInvalidateExisting:
    def test_skips_invalidation_when_replication_disabled(self):
        with (
            patch.object(config.ui, "replication", False),
            patch("clue.services.mongo_service._get_collection") as get_collection,
        ):
            mongo_service.invalidate_existing("user1", "selectors", [], [])

        get_collection.assert_not_called()

    def test_marks_matching_cached_documents_as_deleted(self):
        collection = MagicMock()
        selectors = [Selector(type="ipv4", value="1.2.3.4")]
        sources = [ExternalSource(name="plugin_a", url="http://plugin_a/")]

        with (
            patch.object(config.ui, "replication", True),
            patch("clue.services.mongo_service._get_collection", return_value=collection),
        ):
            mongo_service.invalidate_existing("user1", "selectors", selectors, sources)

        collection.update_many.assert_called_once()
        query, update = collection.update_many.call_args.args
        assert query == {
            "type": {"$in": ["ipv4"]},
            "value": {"$in": ["1.2.3.4"]},
            "source": {"$in": ["plugin_a"]},
            "_deleted": False,
        }
        assert update["$set"]["_deleted"] is True
        assert update["$set"]["updated_at"]

    def test_silently_ignores_mongo_runtime_errors(self):
        selectors = [Selector(type="ipv4", value="1.2.3.4")]

        with (
            patch.object(config.ui, "replication", True),
            patch("clue.services.mongo_service._get_collection", side_effect=ClueRuntimeError("no db")),
        ):
            mongo_service.invalidate_existing("user1", "selectors", selectors, [])
