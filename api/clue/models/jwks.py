from typing import Any, NamedTuple


class JWKSSnapshot(NamedTuple):
    """An immutable-by-convention generation of provider keys and the times they were fetched.

    Keys and timestamps are bundled so a reader that holds one snapshot always judges key age by the
    timestamps captured with those keys, never by a newer refresh. Instances must not be mutated after
    they are published to the cache or the pinned fallback.

    Attributes:
        jwks: JWK dictionaries keyed by `kid`.
        providers: The OAuth provider name that owns each `kid`.
        timestamps: Monotonic time of each provider's last successful fetch, keyed by provider name.
    """

    jwks: dict[str, dict[str, Any]]
    providers: dict[str, str]
    timestamps: dict[str, float]
