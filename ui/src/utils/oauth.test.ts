import { describe, expect, it } from 'vitest';
import { buildOAuthCallbackParams, getSafeRedirectDestination, isSafeRedirectDestination } from './oauth';

describe('buildOAuthCallbackParams', () => {
  it('forwards only allowlisted callback parameters', () => {
    const search = new URLSearchParams({
      provider: 'keycloak',
      code: 'auth-code',
      state: 'server-state',
      session_state: 'session',
      iss: 'https://issuer.invalid',
      nonce: 'attacker-nonce',
      refresh_token: 'attacker-refresh',
      id_token: 'attacker.id.token',
      access_token: 'attacker-access',
      grant_type: 'refresh_token',
      anything: 'else'
    });

    const params = buildOAuthCallbackParams(search);

    expect(Object.fromEntries(params.entries())).toEqual({
      provider: 'keycloak',
      code: 'auth-code',
      state: 'server-state',
      session_state: 'session',
      iss: 'https://issuer.invalid'
    });
  });

  it('forwards a single value for repeated parameters', () => {
    const search = new URLSearchParams('provider=keycloak&code=first&code=second&state=s');

    expect(buildOAuthCallbackParams(search).getAll('code')).toEqual(['first']);
  });

  it('forwards provider errors', () => {
    const search = new URLSearchParams({ provider: 'keycloak', state: 's', error: 'access_denied' });

    expect(buildOAuthCallbackParams(search).get('error')).toBe('access_denied');
  });
});

describe('getSafeRedirectDestination', () => {
  it.each([
    ['/fetchers', undefined, '/fetchers'],
    ['/fetchers', '', '/fetchers'],
    ['/fetchers', '?type=ip&value=1.1.1.1', '/fetchers?type=ip&value=1.1.1.1'],
    ['/', null, '/']
  ])('accepts local destination %s%s', (pathname, search, expected) => {
    expect(getSafeRedirectDestination(pathname, search)).toBe(expected);
  });

  it.each([
    ['/login', '?provider=keycloak&code=c&state=s'],
    ['/login', ''],
    ['/login/', ''],
    ['/LOGIN', ''],
    ['/logout', ''],
    ['/fetchers', '?code=c&state=s'],
    ['/fetchers', '?state=s'],
    ['/fetchers', '?id_token=a.b.c'],
    ['/fetchers', '?access_token=token'],
    ['/fetchers', '?refresh_token=token'],
    ['/fetchers', '?Refresh_Token=token'],
    ['/fetchers', '?nonce=n'],
    ['/fetchers', '?error=access_denied&error_description=x'],
    ['/fetchers', '?session_state=x'],
    ['/fetchers', 'code=c'],
    ['//evil.invalid/path', ''],
    ['/\\evil.invalid', ''],
    ['https://evil.invalid/', ''],
    ['javascript:alert(1)', ''],
    ['/fetchers?code=c', ''],
    ['/fetchers', '?x=1#access_token=t'],
    [null, ''],
    [undefined, ''],
    [{ pathname: '/' }, ''],
    ['/fetchers', { search: '?x' }]
  ])('rejects unsafe destination %s %s', (pathname, search) => {
    expect(getSafeRedirectDestination(pathname, search)).toBeNull();
  });

  it('rejects destinations whose fragment carries OAuth credentials', () => {
    expect(isSafeRedirectDestination('/fetchers', '', '#access_token=t&id_token=a.b.c')).toBe(false);
    expect(isSafeRedirectDestination('/fetchers', '', '#section')).toBe(true);
  });
});
