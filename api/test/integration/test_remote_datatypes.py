import time
from threading import Thread

from clue.common.uid import get_random_id


# noinspection PyShadowingNames
def test_expiring_hash(redis_connection):
    if redis_connection:
        from clue.remote.datatypes.hash import ExpiringHash

        with ExpiringHash("test-expiring-hashmap", ttl=1) as eh:
            assert eh.add("key", "value") == 1
            assert eh.length() == 1
            time.sleep(1.1)
            assert eh.length() == 0


# noinspection PyShadowingNames
def test_sets(redis_connection):
    if redis_connection:
        from clue.remote.datatypes.set import Set

        with Set("test-set") as s:
            s.delete()

            values = ["a", "b", 1, 2]
            assert s.add(*values) == 4
            assert s.length() == 4
            for x in s.members():
                assert x in values
            assert s.random() in values
            assert s.exist(values[2])
            s.remove(values[2])
            assert not s.exist(values[2])
            pop_val = s.pop()
            assert pop_val in values
            assert not s.exist(pop_val)
            assert s.length() == 2

            assert s.limited_add("dog", 3)
            assert not s.limited_add("cat", 3)
            assert s.exist("dog")
            assert not s.exist("cat")
            assert s.length() == 3

            for pop_val in s.pop_all():
                assert pop_val in values or pop_val in ["cat", "dog"]
            assert s.pop() is None
            assert s.length() == 0


# noinspection PyShadowingNames


def test_expiring_sets(redis_connection):
    if redis_connection:
        from clue.remote.datatypes.set import ExpiringSet

        with ExpiringSet("test-expiring-set", ttl=1) as es:
            es.delete()

            values = ["a", "b", 1, 2]
            assert es.add(*values) == 4
            assert es.length() == 4
            assert es.exist(values[2])
            for x in es.members():
                assert x in values
            time.sleep(1.1)
            assert es.length() == 0
            assert not es.exist(values[2])


# noinspection PyShadowingNames
def test_comms_queue(redis_connection):
    if redis_connection:
        from clue.remote.datatypes.queues.comms import CommsQueue

        def publish_messages(message_list):
            time.sleep(0.1)
            with CommsQueue("test-comms-queue") as cq_p:
                for message in message_list:
                    cq_p.publish(message)

        msg_list = ["bob", 1, {"bob": 1}, [1, 2, 3], None, "Nice!", "stop"]
        t = Thread(target=publish_messages, args=(msg_list,))
        t.start()

        with CommsQueue("test-comms-queue") as cq:
            x = 0
            for msg in cq.listen():
                if msg == "stop":
                    break

                assert msg == msg_list[x]

                x += 1

        t.join()
        assert not t.is_alive()


# noinspection PyShadowingNames
def test_user_quota_tracker(redis_connection):
    if redis_connection:
        from clue.remote.datatypes.user_quota_tracker import UserQuotaTracker

        max_quota = 3
        timeout = 2
        name = get_random_id()
        uqt = UserQuotaTracker("test-quota", timeout=timeout)

        # First 0 to max_quota items should succeed
        for _ in range(max_quota):
            assert uqt.begin(name, max_quota) is True

        # All other items should fail until items timeout
        for _ in range(max_quota):
            assert uqt.begin(name, max_quota) is False

        # if you remove and item only one should be able to go in
        uqt.end(name)
        assert uqt.begin(name, max_quota) is True
        assert uqt.begin(name, max_quota) is False

        # if you wait the timeout, all items can go in
        time.sleep(timeout + 1)
        for _ in range(max_quota):
            assert uqt.begin(name, max_quota) is True
