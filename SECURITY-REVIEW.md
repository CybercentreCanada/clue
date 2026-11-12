# CLUE-003 Security Review

**Review date:** 2026-11-12
**Branch:** `fix/SPBK-4316/CLUE-003`
**Base:** `github/develop` / `HEAD` at `820c429`
**Scope:** Read-only review of the unstaged working-tree changes and relevant authentication, classification, and authorization flows. No runtime tests or non-local requests were performed.

## Executive verdict

**Partially confirmed.** Before the working-tree changes, API-key authentication copied `X-USERID`, `X-CLASSIFICATION`, `X-USERNAME`, and `X-EMAIL` directly into the authenticated principal. The reported identity and classification values were therefore reproducible, but those headers did not grant administrator roles or privileges.

The current changes normally bound an impersonated API-key request to server-configured key classification and, when available, the key owner's OAuth-recorded clearance. However, a clearance-store read error is treated like an absent clearance record. If the key's configured classification exceeds the owner's recorded clearance, a valid key holder can then request and receive a principal at the higher key classification. This can expose higher-classified data when classification enforcement is enabled.

The OAuth `classification_map` is not introduced by this patch and does not execute in `validate_apikey`. OAuth authentication can record a clearance that the API-key path later consults, so the relationship is indirect. That mapping does not resolve the store-error fail-open.

### Verdict by reported behavior

| Question | Verdict |
|---|---|
| API-key identity spoofing | Confirmed as header-controlled impersonation; not role elevation. |
| API-key classification escalation | Partially confirmed: normally bounded, but the owner ceiling is dropped on clearance-store read failure. |
| Privilege/role escalation | Not demonstrated; roles and privileges come from server-side key configuration. |
| Unauthorized higher-classified data access | Conditionally confirmed when the key ceiling exceeds the owner's recorded clearance, the clearance lookup fails, and classification enforcement is enabled. |
| Audit/attribution spoofing | Partially confirmed: the claimed username is logged as acting on behalf of that identity, while the API key remains identified. |
| OAuth `classification_map` remediates CLUE-003 | Partly and indirectly; it may supply a stored owner ceiling but does not run in API-key authentication. |

## Data flows

### API-key flow

```text
Basic API-key name/secret [client supplied]
→ exact configured-key lookup and constant-time secret comparison [server config]
→ configured identity, or optional X-USERID/X-USERNAME/X-EMAIL impersonation [headers are client controlled]
→ owner clearance from Redis, if available, plus configured key classification [server-side values]
→ requested X-CLASSIFICATION [client controlled]
→ normalized request checked against available ceilings [fails open for a clearance-store error]
→ configured roles/privileges [server config; not derived from headers]
→ route and classification checks
→ protected operation / filtered result
```

### OAuth flow

```text
OIDC bearer token
→ JWT decode using configured JWK and audience [signature/audience checked; explicit issuer check not established]
→ identity and groups from decoded claims [verified token claims, subject to issuer configuration]
→ server-configured classification_map [derived classification]
→ clearance stored by username when the provider has a non-empty map [Redis]
→ API-key authentication may later consult that record as an owner ceiling [indirect]
→ authorization and classification filtering
```

## API-key identity and authorization

| Field | Source and trust | Effect |
|---|---|---|
| Key name and secret | Client-supplied Basic Authorization; name matched against server config and secret checked with `hmac.compare_digest`. | A valid secret is required. |
| User ID (`uname`) | Configured identity or key name when not impersonating; otherwise client-controlled `X-USERID`. | Header identity is accepted when impersonation is enabled. |
| Display name and email | Configured values or client-controlled `X-USERNAME` / `X-EMAIL` during impersonation. | Metadata and attribution; does not assign roles. |
| Owner | Server-configured `owner`, falling back to configured `uname`, then key name. | Selects which recorded clearance is queried. |
| Trusted maximum | Configured key classification plus an available Redis clearance for the owner. | Lookup errors are treated as no clearance and remove that ceiling. |
| Requested classification | Client-controlled `X-CLASSIFICATION` during impersonation. | Normalized and checked against available ceilings; a lower request is supported. |
| Effective classification | Accepted requested value, or configured key classification for non-impersonated requests. | Used by CLUE's classification checks. |
| Roles and privileges | Server-side API-key configuration; default is `USER` and `R/W`. | Not controlled by identity/classification headers. Admin role requires trusted configuration. |
| Tenant, organization, network zone | No binding or enforcement established in the reviewed API-key policy/authentication path. | Any segmentation is a deployment control, not a demonstrated key-specific application control. |

CLUE uses its classification parser/comparator rather than lexical string ordering. A valid requested classification at or below available ceilings is allowed; a request above them is rejected. The defect is that an unavailable clearance lookup is not distinguished from a genuinely absent record.

## Changes reviewed

- [`api/clue/models/auth_user.py`](api/clue/models/auth_user.py#L20) adds API-key policy fields including configured identity, owner, classification, impersonation flag, roles, privileges, and secret. `allow_impersonation` defaults to `True`.
- [`api/clue/models/config.py`](api/clue/models/config.py#L213) types API-key configuration, converts legacy string secrets to policy objects, and validates configured classifications. `classification_map` is an existing OAuth provider setting, not a change in this patch.
- [`api/clue/services/auth_service.py`](api/clue/services/auth_service.py#L178) changes API-key principal construction and applies configured policy and classification ceiling checks. OAuth authentication records clearance after token authentication.
- [`api/clue/services/user_service.py`](api/clue/services/user_service.py#L24) adds clearance recording and retrieval. A non-empty provider map allows a mapped clearance to be recorded; map-less OAuth authentication does not create a new record.
- [`api/test/unit/services/test_auth_service_security.py`](api/test/unit/services/test_auth_service_security.py#L145) covers configured identities, impersonation, classification ceilings, and clearance recording/lookup. Its lookup-error test checks the getter returns `None`, but does not exercise authorization with a higher key ceiling and a failing lookup.
- Documentation changes describe API-key owners, impersonation, classifications, and map-less behavior in the English/French backend and Helm docs.

## Finding

### 1. Clearance lookup failure removes the owner ceiling

**Severity:** MEDIUM
**Confidence:** 9/10
**CWE:** CWE-863 — Incorrect Authorization

[`get_user_clearance`](api/clue/services/user_service.py#L51) catches clearance-store errors and returns `None`. The API-key classification check in [`_get_impersonated_classification`](api/clue/services/auth_service.py#L265) removes missing ceilings. Consequently, a store error is treated like no recorded owner clearance; the configured key classification may become the only ceiling.

If a valid API-key holder can reach this path, the key's configured classification is above the owner's recorded OAuth clearance, and the clearance store errors, the caller can request a classification above that owner clearance. The resulting principal classification controls classified response filtering in [`QueryResult`](api/clue/models/network.py#L547) and is used in action/fetcher classification checks ([`action_service.py`](api/clue/services/action_service.py#L156), [`fetcher_service.py`](api/clue/services/fetcher_service.py#L172)). Network result filtering can be disabled by classification configuration, so data-access impact is configuration-dependent.

**Minimum remediation:** Distinguish an unavailable clearance store from a genuinely absent record. Fail closed when a required owner-clearance read fails; retain any intentional configured-key fallback only for the explicitly supported no-record case.

### Identity headers and deployment boundary

CLUE reads the impersonation headers directly; no proxy-origin authentication, header stripping, or direct-app-access prevention was established in the reviewed code. A client with a valid key and network reachability can supply these headers. Whether ingress strips caller-supplied values and injects trusted ones is unknown and must be treated as a deployment requirement, not an application-enforced protection.

Identity-header spoofing is not reported as a separate authorization finding here: it does not change key roles or privileges, and audit records retain the API-key identity while labeling activity as being on behalf of the asserted username. A configured OBO extension receives the asserted username; whether an extension treats it as an authorization identity was not established.

## Evidence summary

| Security property | Result | Notes |
|---|---|---|
| API key validated as a secret | Yes | Exact configured-key lookup and constant-time secret comparison. |
| Key bound to trusted identity | Partly | Configured identity absent impersonation; caller headers can override identity fields. |
| Key bound to trusted maximum clearance | Normally | Key classification and optional stored owner clearance; lookup errors drop the owner ceiling. |
| Client headers control identity/classification | Yes | `X-USERID`, `X-USERNAME`, `X-EMAIL`, and `X-CLASSIFICATION`, when impersonation is enabled. |
| Client headers control roles/privileges | No | Roles and privileges are server-configured. |
| Lower requested classification supported | Yes | Normalized and compared with CLUE's classification logic. |
| Higher classification rejected | Normally; not on clearance lookup failure | The error is conflated with no stored clearance. |
| Application resource classification checks | Yes, subject to configuration | Response, action, and fetcher checks use the authenticated principal classification. |
| Proxy/header trust technically enforced | No evidence | Requires deployment controls if a proxy is relied upon. |
| OAuth group mapping based on verified inputs | Mostly | Decode uses configured JWK and audience; explicit issuer validation was not established. |
| No-map fallback safe | Only for a genuine absence of a clearance record and intentional key policy | Store errors are incorrectly treated the same as no record. |
| OAuth map update fixes the API-key path | Partial and indirect | OAuth writes a value that the API-key path may later read. |

## OAuth and other considerations

- `get_dynamic_classification` processes mapped groups and combines valid mapped values. Invalid mappings are skipped; no incorrect multi-group result was established.
- Clearance writes are keyed by username and the shown Redis `Hash` writes have no expiry. Authentication can refresh the stored value, but immediate revocation/freshness semantics are not established. This was not classified as a separate confirmed finding without evidence of the intended revocation policy.
- Multiple OAuth providers sharing a username use the same username-keyed clearance record. Whether such provider identities are intended to be distinct was not established.
- The map-less case creates no new clearance record; when no stored value exists, an unset API-key classification falls back to the lowest level. Existing records are not deleted when the map disappears and remain subject to the configured key cap.

## Impact, severity, and CWE

- **Confidentiality:** Conditional higher-classified data access through the clearance-store error path.
- **Integrity:** No header-based role escalation demonstrated; effects remain bounded by configured privileges and service-level classification checks. Downstream effects depend on configured integrations.
- **Availability:** No finding.
- **Auditability:** Caller-supplied usernames can influence attribution, but the API key is also identified.
- **CWE-863** best describes the demonstrated incorrect authorization. CWE-290 and CWE-639 are not established by the evidence: key authentication still occurs, and no user-specific protected-resource lookup was demonstrated.
- The reported **Critical / 9.1** severity is not justified by demonstrated impact. The access condition requires a valid key, a higher configured key classification than the owner's recorded clearance, a clearance-store read failure, and classification enforcement.

## Recommendations

- **Required to fix an exploitable vulnerability:** Fail closed on clearance-store errors, distinguishing them from a legitimate absence of a record.
- **Defense in depth:** Define clearance freshness/revocation semantics and add a regression test for a high-classification key, lower owner clearance, and failing store lookup. Include tests that lower requested classifications remain allowed and explicit no-record fallback behaves as intended.
- **Deployment/infrastructure requirement:** If relying on a proxy, strip client-supplied identity headers before injecting trusted values and prevent direct access that bypasses that proxy.
- **Defense in depth:** Consider provider-scoped clearance records if same-username identities from different providers are meant to be distinct.
