# CLUE-010 security re-verification

## Scope

- Branch: `fix/SPBK-4307/CLUE-010`
- Base: `github/develop`
- Reviewed: commit `eabea1d` plus the staged remediation changes
  (27 files, API, UI, docs, demo and MCP config)
- Vulnerabilities: CWE-352 (login CSRF) and CWE-294 (capture-replay)
- Authlib version inspected: 1.6.12 (installed in the API Poetry environment)

This review supersedes the previous `SECURITY-REVIEW.md` (commit `eabea1d`),
which found that callback query parameters could select the refresh-token
grant and bypass state validation. That finding is resolved by the staged
changes.

## Verdict

**REQUEST CHANGES — CI blocker only.** The security remediation is complete:
no exploitable login-CSRF or replay path was found. The branch fails the API
workflow because of a ruff E501 introduced in
[auth.py](api/clue/api/v1/auth.py) line 259. All security findings below are
non-blocking.

Correction to the original issue: on `develop`, the authorization-code path
already validated `state` through Authlib's `authorize_access_token`. The
exploitable gap was `login()` accepting `refresh_token` from the query string,
which skipped state validation. This branch moves refresh to a JSON-only
`POST /api/v1/auth/refresh` and rejects non-allowlisted login parameters.

## Validation performed

| Check | Result |
|-------|--------|
| Backend auth unit tests (`test_auth_service_security`, `test_jwt_service`, `test_oauth_roles`, `unit/security`, `test_config`) | 188 passed |
| UI tests (`oauth.test.ts`, `useLogin.test.tsx`, `api/index.test.ts`) | 73 passed |
| `poetry run type_check` (mypy) | Clean |
| `ruff format --check clue` | Clean |
| `ruff check clue` | **1 error: E501 at `auth.py:259` (new on this branch)** |
| Prettier / ESLint on changed UI files | Clean |
| `tsc` on changed UI files | Only the `'url'` import error, also present on `develop` |
| `harness/test_CLUE_010_oauth_nonce.py` | **Not found anywhere on disk** |

Runtime probes (temporary tests using the existing Flask/Authlib fixture,
since deleted) confirmed findings L3 and L5 below.

## Findings

| # | Severity | File | Lines | Issue | Confidence |
|---|----------|------|-------|-------|------------|
| B1 | BLOCKING (CI) | [auth.py](api/clue/api/v1/auth.py) | 259 | Ruff E501: 134-character nested f-string for `redirect_uri` | 10/10 |
| M1 | MEDIUM | [oidc.py](api/clue/security/oidc.py) | 75-80, 177 | `iss` is required but only checked at login; an upgraded deployment without it rejects every login | 9/10 |
| L1 | LOW | [auth.py](api/clue/api/v1/auth.py) | 255-260 | `redirect_uri` host taken from Referer/Host (also on `develop`) | 7/10 |
| L2 | LOW | [app.py](api/clue/app.py) | 118-123 | Session cookie lacks `__Host-` prefix and default SameSite (also on `develop`) | 6/10 |
| L3 | LOW | [auth.py](api/clue/api/v1/auth.py), [error.py](api/clue/error.py) | 155-176, `handle_500` | IdP transport errors return a Python traceback to unauthenticated users (CWE-209, also on `develop`) | 9/10 |
| L4 | LOW | [auth.py](api/clue/api/v1/auth.py) | 161-166 | Attacker-supplied `?error=` value logged unescaped | 6/10 |
| L5 | LOW | [auth.py](api/clue/api/v1/auth.py) | 265-266 | Raw `userinfo` key from the token response trusted for `openid` providers | 9/10 |
| I1 | INFO | [constants.ts](ui/src/lib/utils/constants.ts) | `StorageKey` | `LOGIN_NONCE` deleted from the published library instead of deprecated | 9/10 |
| I2 | INFO | [useLogin.tsx](ui/src/components/logins/hooks/useLogin.tsx) | 98-103 | After a 401, `code`/`state` stay in the URL and no error is shown | 9/10 |
| I3 | INFO | Authlib `framework_integration.py` | — | Replaying an old session cookie is stopped only by the IdP's single-use code | 7/10 |
| I4 | INFO | [auth.py](api/clue/api/v1/auth.py) | 313-316 | Refresh without `id_token` for `openid` providers returns 401 | 6/10 |
| I5 | INFO | [app.py](api/clue/app.py) | 117 | Partially masked `SECRET_KEY` logged at debug level (pre-existing, out of scope) | 8/10 |

### B1. Lint failure blocks CI

CI runs `poetry run ruff check clue`. `develop` built the same value with
`port_portion` and `redirect_uri` local variables; restoring them fixes it.

### M1. Missing `iss` fails every login after upgrade

`ClueOAuth2App._trusted_issuer` raises on every ID-token validation when no
issuer is configured. This fails closed (not exploitable), but deployments
upgrading without `iss` start normally and then reject all logins. Log
critically or fail at startup in `build_oauth` when the scope contains
`openid` and no issuer is set.

### L1. `redirect_uri` derived from Referer/Host

A cross-site page can make the `redirect_uri` host attacker-chosen. This only
matters with a permissive IdP redirect allowlist; a stolen code still cannot
be redeemed because state is bound to the victim's session and a client secret
is required. Build the URI from a configured UI origin.

### L2. Session cookie hardening

The OAuth transaction (state and nonce) lives in the signed Flask session
cookie. Without a `__Host-` prefix, a sibling subdomain could plant its own
signed session. Use `SESSION_COOKIE_NAME="__Host-clue_session"` and default
`SESSION_COOKIE_SAMESITE="Lax"`.

### L3. Stack trace on IdP transport errors

`_handle_auth_errors` does not catch `requests.RequestException`, so it
reaches `handle_500`, which returns the formatted traceback. A probe with the
token endpoint raising `ConnectionError` returned HTTP 500 with file paths and
frames. No tokens or codes were included. Catch the exception and return a
generic error.

### L4. Unescaped attacker-supplied `error` in logs

On a provider-error callback, `OAuthError.error` is the `?error=` value. Log
`repr()` of it, truncated.

### L5. Raw `userinfo` accepted from the token response

`"userinfo" in token_data` also matches a raw `userinfo` key in the token
endpoint JSON. A probe returning `{"access_token": ..., "userinfo": {...}}`
with no `id_token` logged the user in (HTTP 200) even though the provider
requests `openid`. Exploitation requires a malicious or intercepted token
endpoint, but it breaks the "only verified identity is consumed" rule. Accept
only a `UserInfo` produced by `parse_id_token`.

### I1–I5

- **I1:** commit `06fd510` kept `LOGIN_NONCE` as `@deprecated`; the staged
  change deletes it. `src/lib/**` is published, so either restore the
  deprecated member or document the breaking change.
- **I2:** on failure, `navigate('/login', { replace: true })` and show
  `user.login.failed`.
- **I3:** confirm the IdP enforces single-use, short-lived codes (Keycloak
  does); optionally enable PKCE (`code_challenge_method: S256`).
- **I4:** some IdPs omit `id_token` on refresh; document the forced re-login.
- **I5:** pre-existing; consider removing the log line separately.

## Requirements checklist

| Requirement | Result | Evidence |
|-------------|--------|----------|
| No browser/query nonce trusted | PASS | `authorize_redirect` passes no nonce; parameter allowlists in `auth.py`; `user_service.py` re-parse removed |
| State validated against session | PASS | Authlib `authorize_access_token` raises `MismatchingStateError`; state removed after use |
| Nonce validated against session | PASS | `ClueOAuth2App._validate_id_token` requires session nonce and `nonce` claim; `parse_id_token` overridden |
| Callback without matching session rejected | PASS | `MismatchingStateError` → `_handle_auth_errors` → 401 |
| Unverified ID tokens not consumed | PASS (gap L5) | `auth.py` 265-271 |
| Signature and claims validation enforced | PASS | Asymmetric algorithms, exact `iss`, `aud` contains client ID, `sub`/`exp`/`iat`, `at_hash`, `kid` lookup |
| ID-token replay mitigated | PASS | Back-channel ID tokens only; session-bound nonce; single-use state (see I3) |
| UI no longer uses nonce mechanism | PASS | `OAuthLogin.tsx` sends only `oauth_provider`; no runtime nonce use in `ui/src` |
| Callback params not persisted as return URLs | PASS | `isSafeRedirectDestination` in `api/index.ts` and `App.tsx`; `getSafeRedirectDestination` in `useLogin.tsx` |
| Validation failures return controlled errors | PARTIAL | OAuth/JOSE errors → generic 401; transport errors leak a traceback (L3) |
| No sensitive leakage via logs/errors | PASS (minor) | Only error class and code logged; see L4 |

## Browser-controlled inputs

| Input | Handling |
|-------|----------|
| `provider`, `oauth_provider` | Validated against configured providers |
| `code` | Validated by the IdP (single-use) |
| `state` | Looked up in the signed session and removed after use |
| `session_state`, `iss`, `error_description`, `error_uri` | Ignored |
| `error` | Rejected with 401; logged unescaped (L4) |
| `nonce`, `id_token`, `access_token`, `refresh_token`, unknown or repeated parameters | Rejected with 400 |
| Session cookie | Trusted after HMAC signature verification |
| Referer / Host | Trusted for `redirect_uri` host (L1) |
| `/refresh` JSON body | Strict Pydantic model; query and form bodies rejected |
| `NEXT_LOCATION` / `NEXT_SEARCH` | Re-validated before navigation |

## Test gaps

Covered: server nonce, allowlists, repeated parameters, forged/missing/
foreign/reused/cross-provider state, provider errors, 21 invalid-ID-token
cases, `/refresh` strictness, attacker refresh-token link, and UI redirect
safety and 401 handling.

Recommended additions:

- Code exchange uses the session-stored `redirect_uri`.
- Attacker's state redeemed in the victim's browser returns 401 without an
  exchange.
- Raw `userinfo` without `id_token` returns 401 (fails today, L5).
- IdP `ConnectionError` returns no traceback (fails today, L3).
- No code, state, nonce or tokens in logs (`caplog`); `Set-Cookie` attributes.
- UI: `OAuthLogin` link has no nonce and writes no storage; no redemption
  with only `code` or only `error`; URL replaced and error shown after a 401.
- Provide or remove the referenced `harness/test_CLUE_010_oauth_nonce.py`.
