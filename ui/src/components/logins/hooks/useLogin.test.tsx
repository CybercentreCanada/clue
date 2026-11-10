import { act, renderHook } from '@testing-library/react';
import { MY_LOCAL_STORAGE_PREFIX, StorageKey } from 'lib/utils/constants';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import useLogin from './useLogin';

const mocks = vi.hoisted(() => ({
  navigate: vi.fn(),
  setUser: vi.fn(),
  loginGet: vi.fn(),
  saveLoginCredential: vi.fn(),
  location: { pathname: '/login', search: '', hash: '' },
  searchParams: new URLSearchParams()
}));

vi.mock('api', () => ({ default: { auth: { login: { get: mocks.loginGet } } } }));
vi.mock('react-router', () => ({ useNavigate: () => mocks.navigate, useLocation: () => mocks.location }));
vi.mock('react-router-dom', () => ({ useSearchParams: () => [mocks.searchParams] }));
vi.mock('commons/components/app/hooks/useAppUser', () => ({ default: () => ({ setUser: mocks.setUser }) }));
vi.mock('components/hooks/useMyApi', () => ({ default: () => ({ dispatchApi: (call: Promise<any>) => call }) }));
vi.mock('components/hooks/useMyModal', () => ({ default: () => ({ showModal: vi.fn() }) }));
vi.mock('components/hooks/useMySnackbar', () => ({ default: () => ({ showErrorMessage: vi.fn() }) }));
vi.mock('components/elements/display/modals/LoginErrorModal', () => ({ default: () => null }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock('utils/localStorage', () => ({ saveLoginCredential: mocks.saveLoginCredential }));

const store = (key: StorageKey, value: string) =>
  window.localStorage.setItem(`${MY_LOCAL_STORAGE_PREFIX}.${key}`, JSON.stringify(value));
const stored = (key: StorageKey) => window.localStorage.getItem(`${MY_LOCAL_STORAGE_PREFIX}.${key}`);

const credential = { app_token: 'token', user: { name: 'User', groups: [], preferred_username: 'user' } as any };

describe('useLogin', () => {
  beforeEach(() => {
    window.localStorage.clear();
    mocks.location.pathname = '/login';
    mocks.location.search = '';
    mocks.location.hash = '';
    mocks.searchParams = new URLSearchParams();
    mocks.saveLoginCredential.mockReturnValue(true);
  });

  afterEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it('navigates to a safe persisted destination and clears it', () => {
    store(StorageKey.NEXT_LOCATION, '/fetchers');
    store(StorageKey.NEXT_SEARCH, '?type=ip');
    const { result } = renderHook(() => useLogin());

    act(() => result.current.getUser(credential));

    expect(mocks.navigate).toHaveBeenCalledWith('/fetchers?type=ip', { replace: true });
    expect(stored(StorageKey.NEXT_LOCATION)).toBeNull();
    expect(stored(StorageKey.NEXT_SEARCH)).toBeNull();
  });

  it.each([
    ['/login', '?provider=keycloak&code=c&state=s'],
    ['/login', '?provider=keycloak&code=c&state=s&id_token=a.b.c&access_token=t'],
    ['/fetchers', '?refresh_token=attacker'],
    ['/fetchers', '?code=c&state=s'],
    ['//evil.invalid', ''],
    ['https://evil.invalid/', '']
  ])('rejects a previously persisted unsafe destination %s%s', (pathname, search) => {
    store(StorageKey.NEXT_LOCATION, pathname);
    store(StorageKey.NEXT_SEARCH, search);
    const { result } = renderHook(() => useLogin());

    act(() => result.current.getUser(credential));

    expect(mocks.navigate).toHaveBeenCalledTimes(1);
    expect(mocks.navigate).toHaveBeenCalledWith('/', { replace: true });
    expect(stored(StorageKey.NEXT_LOCATION)).toBeNull();
    expect(stored(StorageKey.NEXT_SEARCH)).toBeNull();
  });

  it('forwards only allowlisted callback parameters when redeeming an OAuth code', async () => {
    mocks.location.search =
      '?type=ip&code=c&state=s&session_state=x&iss=https%3A%2F%2Fissuer.invalid&error_description=bad&provider=keycloak&oauth_provider=keycloak';
    mocks.location.hash = '#section';
    mocks.searchParams = new URLSearchParams({
      provider: 'keycloak',
      code: 'c',
      state: 's',
      type: 'ip',
      session_state: 'x',
      iss: 'https://issuer.invalid',
      error_description: 'bad',
      nonce: 'injected-nonce',
      refresh_token: 'injected-refresh',
      id_token: 'injected.id.token',
      access_token: 'injected-access',
      other: 'x'
    });
    mocks.loginGet.mockResolvedValue(credential);
    const { result } = renderHook(() => useLogin());

    await act(() => result.current.doOAuth());

    const forwarded: URLSearchParams = mocks.loginGet.mock.calls[0][0];
    expect(Object.fromEntries(forwarded.entries())).toEqual({
      provider: 'keycloak',
      code: 'c',
      state: 's',
      session_state: 'x',
      iss: 'https://issuer.invalid',
      error_description: 'bad'
    });
    expect(mocks.navigate).toHaveBeenNthCalledWith(1, '/login?type=ip#section', { replace: true });
    expect(mocks.navigate.mock.invocationCallOrder[0]).toBeLessThan(mocks.loginGet.mock.invocationCallOrder[0]);
  });

  it('clears callback params before redeeming an OAuth error response', async () => {
    mocks.location.search =
      '?type=ip&state=s&error=access_denied&error_description=denied&error_uri=https%3A%2F%2Fissuer.invalid%2Ferror';
    mocks.searchParams = new URLSearchParams(
      'type=ip&provider=keycloak&state=s&error=access_denied&error_description=denied&error_uri=https%3A%2F%2Fissuer.invalid%2Ferror'
    );
    mocks.loginGet.mockRejectedValue(new Error('exchange failed'));
    const { result } = renderHook(() => useLogin());

    await act(async () => {
      await expect(result.current.doOAuth()).rejects.toThrow('exchange failed');
    });

    expect(mocks.loginGet.mock.calls[0][0].get('error')).toBe('access_denied');
    expect(mocks.navigate).toHaveBeenNthCalledWith(1, '/login?type=ip', { replace: true });
    expect(mocks.navigate.mock.invocationCallOrder[0]).toBeLessThan(mocks.loginGet.mock.invocationCallOrder[0]);
  });

  it('clears callback params before handling a resolved API error response', async () => {
    mocks.location.search = '?filter=recent&code=c&state=s';
    mocks.loginGet.mockResolvedValue({ api_error_message: 'Authentication failed.' });
    mocks.saveLoginCredential.mockReturnValue(false);
    const { result } = renderHook(() => useLogin());

    await act(() => result.current.doOAuth());

    expect(mocks.navigate).toHaveBeenNthCalledWith(1, '/login?filter=recent', { replace: true });
    expect(mocks.navigate.mock.invocationCallOrder[0]).toBeLessThan(mocks.loginGet.mock.invocationCallOrder[0]);
  });
});
