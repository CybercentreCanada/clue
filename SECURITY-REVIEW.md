# CLUE-010 security verification

## Verdict

**NOT RESOLVED — High confidence.**

Reviewed branch: `fix/SPBK-4307/CLUE-010`, commit
`06fd51056571a10052980a7390ac870998ba1688`. The worktree was clean.

The ordinary authorization-code flow now uses a server-generated nonce and
Authlib's session-bound state validation. However, callback parameters can
select the refresh-token branch and bypass both controls. The original
query-sourced nonce comparison was removed, but login CSRF remains possible.

## Findings

| # | Severity | File | Lines | Vulnerability | Confidence |
|---|----------|------|-------|---------------|------------|
| 1 | MEDIUM | [auth.py](api/clue/api/v1/auth.py) | 165-173 | Callback-selected refresh flow permits login CSRF/session swapping | 9/10 |

### 1. Callback parameters select a state-free refresh login

In `login`, a GET query containing `refresh_token` selects
`fetch_access_token(grant_type="refresh_token")` instead of
`authorize_access_token`. This skips Authlib's state/session validation and
validates the refresh ID token with `nonce=None`.

The browser path makes this reachable:

- [OAuthLogin.tsx](ui/src/components/logins/auth/OAuthLogin.tsx), lines 21-26,
  starts redemption when the URL contains `code`.
- [useLogin.tsx](ui/src/components/logins/hooks/useLogin.tsx), lines 90-94,
  forwards callback parameters and saves the returned credentials.
- [login.ts](ui/src/api/auth/login.ts), lines 27-28, forwards the query object
  without filtering.

An attacker with a valid refresh token for their own permitted account can
send a victim a link shaped as:

```text
/login?provider=<provider>&code=unused&state=forged&refresh_token=<attacker-owned-refresh-token>
```

The victim can be logged into the attacker's account without initiating an
authorization transaction. Subsequent activity may expose account-scoped work
to that attacker or be attributed to the wrong identity. This does not
demonstrate theft of the victim's identity-provider tokens.

A behavioral probe using the real Flask/Authlib fixture, with the token endpoint
mocked, returned **200** for a fresh-session GET containing forged state and an
attacker-owned refresh credential. The exchange received that credential and
`grant_type="refresh_token"`. An in-memory frontend probe confirmed forwarding
of the injected refresh credential.

## Requirements checklist

FAIL includes unmet requirements and unavailable evidence; it does not imply
that every row is an independently exploitable vulnerability.

| # | Result | Evidence |
|---|--------|----------|
| 1 | PASS | `login` initiation in [auth.py](api/clue/api/v1/auth.py), lines 123-130, does not read a client nonce; a behavioral test confirms it is ignored. |
| 2 | PASS, with storage qualification | Authlib generates a cryptographically random 20-character nonce for `openid` scope and stores it with the transaction state. [app.py](api/clue/app.py), line 118, configures the signing key and secure session cookie. Storage is a server-managed, integrity-protected cookie session, not server-side-only storage. |
| 3 | FAIL overall; ordinary flow passes | [auth.py](api/clue/api/v1/auth.py), line 177, uses Authlib's saved transaction nonce, not callback input. Callback-selected refresh bypasses that transaction. |
| 4 | FAIL | Ordinary signature/nonce validation works, but production-style registration accepted a correctly signed token with a wrong issuer, and a wrong audience when `azp` matched the client. |
| 5 | PASS | [auth.py](api/clue/api/v1/auth.py), lines 178-182, rejects an ID token lacking validated `userinfo`; invalid-signature tests return 401. |
| 6 | PASS | [user_service.py](api/clue/services/user_service.py), lines 37-45, no longer performs the request-dependent JWT reparse. Production callers are login and the verified bearer-token path. |
| 7 | FAIL | [auth.py](api/clue/api/v1/auth.py), lines 165-173, uses `nonce=None` on a refresh path selectable from callback queries; remaining claim checks also have gaps. |
| 8 | FAIL | [auth.py](api/clue/api/v1/auth.py), lines 225-227, catches `OAuthError`, `JoseError` and authentication exceptions. Wrong/missing nonce, bad signature, expiry and malformed JWT return 401, but an unknown signing-key ID raises uncaught `ValueError: Key not found`. |
| 9 | FAIL | Nonce generation/storage was removed from the UI, but [useLogin.tsx](ui/src/components/logins/hooks/useLogin.tsx), line 91, still forwards an injected nonce. The backend ignores it. |
| 10 | FAIL | [login.ts](ui/src/api/auth/login.ts), lines 27-28, forwards the complete query object; a frontend probe confirms nonce forwarding. |
| 11 | FAIL | [index.ts](ui/src/api/index.ts), lines 166-168, excludes failed login API requests, not a current login callback URL when another API returns 401. A probe persisted a callback URL with `code`, `state` and `id_token`. [useLogin.tsx](ui/src/components/logins/hooks/useLogin.tsx), lines 50-54, consumes saved destinations without callback filtering. |
| 12 | FAIL overall; ordinary flow passes | Authlib checks provider-specific state in the signed Flask session before code exchange. Forged, missing, foreign-session and reused state return 401 without exchange. Callback-selected refresh bypasses that check. |
| 13 | PASS | Repository-wide searches covered nonce, request nonce access, `LOGIN_NONCE`, `id_token`, `authorize_redirect`, login/callback endpoints and state. Relevant results are recorded below. |
| 14 | PASS: reviewed; bypass found | Refresh, provider-name compatibility, non-OIDC fallback, direct bearer, Basic/API-key, service-account grants, MCP verification and legacy integration tests were reviewed. Refresh exposes finding 1. |
| 15 | FAIL: incomplete evidence | The requested `harness/test_CLUE_010_oauth_nonce.py` and its directory are absent. Available regression tests were inspected and run, but miss important negative cases. |

### Claim-validation and error-handling qualifications

These are demonstrated control gaps, not additional established
attacker-exploitable findings:

- **Issuer:** [config.py](api/clue/models/config.py), line 91, exposes `iss`, but
  provider registration in [app.py](api/clue/app.py), lines 155-183, does not
  translate it into Authlib issuer metadata or claim options. Installed Authlib
  1.6.12 constrains issuer only when metadata contains `issuer`.
- **Audience:** A wrong audience alone returns 401, but a wrong audience with
  `azp` matching the local client returns 200.
- **Nonce exception:** Installed Authlib disables nonce comparison when a signed
  token contains `nonce_supported=false`. A wrong-nonce probe with that signed
  claim returned 200. Browser query input alone cannot set a signed claim.
- **Unknown key:** An unknown `kid` causes an uncaught `ValueError`. Trace
  disclosure or an authentication bypass was not established.

The signed-token probes used locally generated keys standing in for the
provider's trusted signing key. They demonstrate validation behavior, not an
attacker's ability to obtain arbitrary provider-signed claims.

## Test evidence

| Test or probe | Result |
|---------------|--------|
| [Backend security tests](api/test/unit/services/test_auth_service_security.py) | 22 passed |
| [Frontend API tests](ui/src/api/index.test.ts) | 25 passed |
| Two additional in-memory frontend probes | Confirmed nonce/refresh forwarding and callback redirect persistence; combined run 27 passed |
| Fresh-session GET refresh with forged state | 200 |
| Wrong issuer; wrong audience with matching `azp` | 200; 200 |
| Wrong audience alone; expired token; malformed token | 401; 401; 401 |
| Wrong nonce with signed `nonce_supported=false` | 200 |
| Unknown signing-key ID | Unhandled `ValueError` |

The user-supplied read-only 378-line attachment is byte-for-byte identical to
[test_auth_service_security.py](api/test/unit/services/test_auth_service_security.py).
Its OIDC tests meaningfully exercise real Authlib, Flask sessions, signed JWTs
and endpoint responses. They check ordinary nonce/signature validation and
state rejection before exchange, rather than only source patterns.

They do not cover callback-selected refresh, wrong issuer, strict audience
membership, `nonce_supported=false` or unknown signing keys.

The nonce test in [index.test.ts](ui/src/api/index.test.ts), lines 38-55, starts
without a nonce and checks that none appears; it does not test removal of an
injected nonce. Its redirect test, lines 58-65, covers a login-request 401, not
another API request failing while the browser is on a callback URL.

Test discovery initially found no tests; focused runners were used instead.
Python verification disabled external configuration, network connections,
bytecode and pytest cache output. Frontend verification disabled config-file
loading, coverage, cache and file reporters. An initial additional frontend
probe needed correction for an existing `window.location` mock; the corrected
in-memory probe passed. Live identity-provider integration tests were not run.
No application or test files were changed.

## Search and alternate-flow coverage

- Production nonce and ID-token handling is concentrated in
  [auth.py](api/clue/api/v1/auth.py). No request-sourced nonce comparison remains.
- [constants.ts](ui/src/lib/utils/constants.ts), lines 21-22, retains an unused,
  deprecated `LOGIN_NONCE` key.
- Effective ordinary-flow state validation is in installed Authlib's Flask
  `authorize_access_token` implementation, which retrieves provider-specific
  session state and rejects a missing/mismatched transaction before exchange.
- [auth_service.py](api/clue/services/auth_service.py), lines 130-160, handles
  verified direct bearer authentication.
  [MCP auth.py](mcp/clue_mcp/auth.py) separately verifies bearer JWTs. Neither is
  another browser callback implementation.
- [Legacy integration tests](api/test/integration/api/test_auth.py) exercise
  code and direct bearer flows, but were not run against a live provider.
- Documentation and commit descriptions were not treated as proof.

## Recommended next actions

1. Separate refresh from authorization callbacks. Reject refresh credentials in
   callback queries, restrict refresh to the intended POST-body flow and allowlist
   browser callback parameters.
2. Enforce configured issuer, audience membership and required nonce policy
   explicitly; verify the signed `nonce_supported=false` behavior is acceptable.
3. Convert unknown-key validation failures into controlled authentication errors
   without broadly swallowing unrelated exceptions.
4. Never save callback URLs or OAuth credentials as post-login destinations;
   filter both persisted destinations and forwarded callback parameters.
5. Add behavioral negative tests for the demonstrated bypass and validation
   gaps, plus injected nonce forwarding and unrelated-request 401s on callbacks.
   Restore or locate the requested harness before claiming its verification.
