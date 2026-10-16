/**
 * Query parameters forwarded from the browser OAuth callback to the API. Everything else (notably `nonce`,
 * `refresh_token`, `id_token` and `access_token`) is dropped; the API rejects them as well.
 */
export const OAUTH_CALLBACK_PARAMS = [
  'provider',
  'oauth_provider',
  'code',
  'state',
  'session_state',
  'iss',
  'error',
  'error_description',
  'error_uri'
] as const;

/**
 * Query or fragment parameters that mark a URL as an OAuth callback or as carrying OAuth credentials. Such URLs must
 * never be saved or reused as post-login destinations.
 */
export const OAUTH_SENSITIVE_PARAMS = [
  'code',
  'state',
  'session_state',
  'nonce',
  'id_token',
  'access_token',
  'refresh_token',
  'token',
  'error',
  'error_description',
  'error_uri'
] as const;

const AUTH_ROUTES = ['/login', '/logout'];

/**
 * Build the parameters to send to the API for an OAuth callback, keeping only the first value of allowlisted keys.
 */
export const buildOAuthCallbackParams = (search: URLSearchParams): URLSearchParams => {
  const params = new URLSearchParams();
  OAUTH_CALLBACK_PARAMS.forEach(key => {
    const value = search?.get(key);
    if (value !== null && value !== undefined) {
      params.set(key, value);
    }
  });
  return params;
};

const hasSensitiveParams = (raw: string): boolean => {
  const keys = Array.from(new URLSearchParams(raw.replace(/^[?#]/, '')).keys()).map(key => key.toLowerCase());
  return keys.some(key => (OAUTH_SENSITIVE_PARAMS as readonly string[]).includes(key));
};

/**
 * Return a same-origin `pathname + search` post-login destination, or `null` when the destination is unsafe: not a
 * local absolute path, an authentication route, or a URL carrying OAuth callback data or credentials.
 */
export const getSafeRedirectDestination = (pathname: unknown, search?: unknown): string | null => {
  if (typeof pathname !== 'string' || !pathname.startsWith('/') || pathname.startsWith('//')) {
    return null;
  }

  // Backslashes and control characters can be normalized into scheme-relative or cross-origin URLs by browsers.
  // eslint-disable-next-line no-control-regex
  if (/[\\\u0000-\u001f]/.test(pathname)) {
    return null;
  }

  const normalizedPath = pathname.replace(/\/+$/, '').toLowerCase() || '/';
  if (AUTH_ROUTES.some(route => normalizedPath === route || normalizedPath.startsWith(`${route}/`))) {
    return null;
  }

  if (pathname.includes('?') || pathname.includes('#')) {
    return null;
  }

  if (search === null || search === undefined || search === '') {
    return pathname;
  }

  if (typeof search !== 'string' || !search.startsWith('?') || search.includes('#') || hasSensitiveParams(search)) {
    return null;
  }

  return `${pathname}${search}`;
};

/**
 * Whether the given location is a safe post-login destination. See {@link getSafeRedirectDestination}.
 */
export const isSafeRedirectDestination = (pathname: unknown, search?: unknown, hash?: unknown): boolean =>
  getSafeRedirectDestination(pathname, search) !== null && !(typeof hash === 'string' && hasSensitiveParams(hash));
