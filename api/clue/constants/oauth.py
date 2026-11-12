"""Request parameter sets and messages for the OAuth login and token refresh endpoints."""

OAUTH_PROVIDER_PARAMS = frozenset({"provider", "oauth_provider"})
# Parameters an authorization server may append to the redirect URI: RFC 6749 section 4.1.2 (code, state, error*),
# OIDC Session Management (session_state) and RFC 9207 (iss). Anything else, notably credentials such as
# refresh_token, id_token or access_token, is rejected before any token exchange.
OAUTH_CALLBACK_PARAMS = OAUTH_PROVIDER_PARAMS | frozenset(
    {"code", "state", "session_state", "iss", "error", "error_description", "error_uri"}
)
# Transitional: UIs released before CLUE-010 add their own nonce to the login link and to the callback. It is accepted
# (once) so a cached UI can still sign in, then discarded: it is never read, so it cannot reach Authlib, the session or
# ID-token validation, which only use the nonce Authlib generated and stored for this browser session.
LEGACY_IGNORED_LOGIN_PARAMS = frozenset({"nonce"})
# Presence of any of these makes the request an authorization callback rather than a login initiation.
OAUTH_CALLBACK_MARKERS = frozenset({"code", "state", "error"})
