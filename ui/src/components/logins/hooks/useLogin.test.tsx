import { act, renderHook } from '@testing-library/react';
import { MY_LOCAL_STORAGE_PREFIX, StorageKey } from 'lib/utils/constants';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import useLogin from './useLogin';

const mocks = vi.hoisted(() => ({
  navigate: vi.fn(),
  setUser: vi.fn(),
  loginGet: vi.fn(),
  saveLoginCredential: vi.fn(),
  location: { pathname: '/login', search: '' },
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
    mocks.searchParams = new URLSearchParams({
      provider: 'keycloak',
      code: 'c',
      state: 's',
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
    expect(Object.fromEntries(forwarded.entries())).toEqual({ provider: 'keycloak', code: 'c', state: 's' });
  });
});
