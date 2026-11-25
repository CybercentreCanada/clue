import hashlib

from clue.remote.datatypes import get_client, retry_call

# Atomically checks and updates an identifier's lockout state so concurrent requests can't slip past the limit.
# KEYS: lockout flag, failure counter, lockout counter. ARGV: max failures, window, max lockout, failed (0/1).
# While locked out, attempts are neither checked nor counted, so a lockout can't be extended (by retries or
# otherwise) and can't be used to test guesses. Each repeated lockout of the same identifier doubles in length.
lockout_script = """
if redis.call('EXISTS', KEYS[1]) == 1 then
    return 1
end

if ARGV[4] == '1' then
    local max_failures, window, max_lockout = tonumber(ARGV[1]), tonumber(ARGV[2]), tonumber(ARGV[3])
    local failures = redis.call('INCR', KEYS[2])
    if failures == 1 then
        redis.call('EXPIRE', KEYS[2], window)
    end

    if failures >= max_failures then
        redis.call('DEL', KEYS[2])
        local lockouts = redis.call('INCR', KEYS[3])
        local duration = math.floor(math.min(window * 2 ^ math.min(lockouts - 1, 32), max_lockout))
        redis.call('SET', KEYS[1], '1', 'EX', duration)
        redis.call('EXPIRE', KEYS[3], duration + max_lockout)
    end
end

return 0
"""


class Lockout(object):
    """Tracks failed attempts per identifier in Redis and locks the identifier out with exponential backoff."""

    def __init__(self, prefix: str, redis=None, host=None, port=None, private=False):
        self.c = redis or get_client(host, port, private)
        self.ls = self.c.register_script(lockout_script)
        self.prefix = prefix

    def keys(self, identifier: str) -> list[str]:
        """Get the lockout flag, failure counter and lockout counter keys for the identifier."""
        identifier_hash = hashlib.sha256(identifier.encode("utf-8", errors="replace")).hexdigest()
        return [f"{self.prefix}_{kind}_{identifier_hash}" for kind in ("lockout", "failures", "lockouts")]

    def check(
        self, identifier: str, failed: bool, max_failures: int, window_seconds: int, max_lockout_seconds: int
    ) -> bool:
        """Check whether the identifier is locked out, counting this attempt if it failed.

        Args:
            identifier: The identifier (e.g. a client IP) to check.
            failed: Whether this attempt failed.
            max_failures: Number of failures within the window that triggers a lockout.
            window_seconds: Failure counting window, and the duration of the first lockout.
            max_lockout_seconds: Upper bound on a lockout's duration.

        Returns:
            True if the identifier is locked out.
        """
        return bool(
            retry_call(
                self.ls,
                keys=self.keys(identifier),
                args=[max_failures, window_seconds, max_lockout_seconds, int(failed)],
            )
        )
