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
    ['/fetchers', '?refresh_token=attacker'],
    ['//evil.invalid', '']
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

  it('removes the OAuth callback from the URL before redeeming the code', async () => {
    mocks.location.search = '?type=ip&code=c&state=s&session_state=x&provider=keycloak';
    mocks.location.hash = '#section';
    mocks.searchParams = new URLSearchParams({ provider: 'keycloak', code: 'c', state: 's', type: 'ip' });
    mocks.loginGet.mockResolvedValue(credential);
    const { result } = renderHook(() => useLogin());

    await act(() => result.current.doOAuth());

    expect(mocks.loginGet).toHaveBeenCalledWith(mocks.searchParams);
    expect(mocks.navigate).toHaveBeenNthCalledWith(1, '/login?type=ip#section', { replace: true });
    expect(mocks.navigate.mock.invocationCallOrder[0]).toBeLessThan(mocks.loginGet.mock.invocationCallOrder[0]);
  });

  it.each([
    [
      'a provider error',
      '?type=ip&state=s&error=access_denied&error_uri=x',
      () => mocks.loginGet.mockRejectedValue(new Error('failed'))
    ],
    ['an API error', '?type=ip&code=c&state=s', () => mocks.loginGet.mockResolvedValue({ api_error_message: 'failed' })]
  ])('clears callback params before redeeming %s', async (_, search, mockResponse) => {
    mocks.location.search = search;
    mocks.searchParams = new URLSearchParams(search);
    mocks.saveLoginCredential.mockReturnValue(false);
    mockResponse();
    const { result } = renderHook(() => useLogin());

    await act(() => result.current.doOAuth().catch(() => undefined));

    expect(mocks.navigate).toHaveBeenNthCalledWith(1, '/login?type=ip', { replace: true });
    expect(mocks.navigate.mock.invocationCallOrder[0]).toBeLessThan(mocks.loginGet.mock.invocationCallOrder[0]);
  });

  it.each(['#access_token=t', '#id_token=a.b.c&refresh_token=r', '#ACCESS_TOKEN=t', '#section&token=t'])(
    'clears credential fragment %s while preserving a denied callback for the API',
    async hash => {
      mocks.location.search = '?type=ip&provider=keycloak&state=s&error=access_denied';
      mocks.location.hash = hash;
      mocks.searchParams = new URLSearchParams(mocks.location.search);
      const error = new Error('Authentication failed.');
      mocks.loginGet.mockRejectedValue(error);
      const { result } = renderHook(() => useLogin());

      await act(async () => {
        await expect(result.current.doOAuth()).rejects.toBe(error);
      });

      expect(mocks.navigate).toHaveBeenCalledWith('/login?type=ip', { replace: true });
      expect(mocks.loginGet).toHaveBeenCalledWith(mocks.searchParams);
      expect(mocks.loginGet.mock.calls[0][0].get('error')).toBe('access_denied');
      expect(mocks.navigate.mock.invocationCallOrder[0]).toBeLessThan(mocks.loginGet.mock.invocationCallOrder[0]);
      expect(mocks.saveLoginCredential).not.toHaveBeenCalled();
    }
  );
});
