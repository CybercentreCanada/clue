# Security review: plugin type-discovery cache

## Scope and result

Reverified on `main` at `24b3757` on 2026-11-18: the finding is still open.
This review covers the plugin `/types/` cache path only. No runtime tests
were run and no external systems were contacted.

| # | Severity | File | Lines | Vulnerability | Confidence |
|---|----------|------|-------|---------------|------------|
| 1 | 🟡 MEDIUM | [type_service.py](api/clue/services/type_service.py#L70) | 70-72, 109-113 | Plugin type-discovery responses share a URL-only Redis cache across authorization contexts | 10/10 |

## Evidence

- `get_supported_types` accepts the caller's access token and OBO token.
  Its outer memoization includes those arguments, but the inner Redis lookup
  uses only `CACHE.get(url)`, before constructing authentication headers or
  contacting the plugin.
- Successful responses are stored with `CACHE.set(url, types_result)`.
- [RedisCache](api/clue/remote/datatypes/cache.py#L20) constructs keys as
  `prefix-name`, yielding `clue_types-<URL>` without an authorization context.
- [Header generation](api/clue/helper/headers.py#L21) selects the OBO token,
  falling back to the caller's access token.
- The production TTL is 300 seconds (one second in debug mode).
  [Cache hits refresh the TTL](api/clue/remote/datatypes/cache.py#L32), so
  repeated Redis hits can extend reuse beyond five minutes from insertion.

## Impact and limitations

If a plugin returns different supported types or classification mappings
depending on the caller, a subsequent caller can receive the cached response
without the plugin authorizing that caller's discovery request. This can
expose type availability or suppress types that the subsequent caller should
have received.

Clue still checks source classification, prepares the requesting user's
tokens, restricts returned names to recognized types, and applies per-type
classification filtering in its exposed type-discovery results. Those checks
do not reproduce arbitrary caller-specific authorization performed by a
plugin.

The shared-cache mechanism is source-verified. Actual disclosure depends on a
configured plugin whose response or access decision varies by caller, and on
shared cache reads being enabled. The [stock plugin handler](api/clue/plugin/__init__.py#L854)
returns configured types and classifications without using caller identity.
This review does not demonstrate disclosure of enrichment records, credential
theft, or unauthorized downstream operations.

## Recommended follow-up

Bypass both cache layers for caller-dependent discovery. If caching is
necessary, scope both layers to the plugin URL and effective authorization
context; use a keyed digest rather than raw credentials in cache keys.
Invalidate legacy URL-only entries during rollout and add a focused regression
test for cache isolation.

No application code or configuration was changed as part of this review.
