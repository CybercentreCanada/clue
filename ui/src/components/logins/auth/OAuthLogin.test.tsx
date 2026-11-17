import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OAuthLogin from './OAuthLogin';

const mocks = vi.hoisted(() => ({ doOAuth: vi.fn(), location: { search: '', hash: '' } }));

vi.mock('../hooks/useLogin', () => ({ default: () => ({ doOAuth: mocks.doOAuth }) }));
vi.mock('react-router', () => ({ useLocation: () => mocks.location }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));

// Only the click's side effects matter; jsdom cannot follow the link.
const preventNavigation = (event: Event) => event.preventDefault();

const renderLogin = async (providers: string[]) => {
  await act(async () => {
    render(<OAuthLogin providers={providers} />);
  });
};

describe('OAuthLogin', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    mocks.location.search = '';
    mocks.location.hash = '';
    document.addEventListener('click', preventNavigation);
  });

  afterEach(() => {
    document.removeEventListener('click', preventNavigation);
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it('starts a login with only the provider parameter', async () => {
    await renderLogin(['keycloak', 'azure_ad']);

    const links = screen.getAllByRole('link').map(link => new URL(link.getAttribute('href'), window.location.origin));
    expect(links.map(link => link.pathname)).toEqual(['/api/v1/auth/login', '/api/v1/auth/login']);
    expect(links.map(link => [...link.searchParams.entries()])).toEqual([
      [['oauth_provider', 'keycloak']],
      [['oauth_provider', 'azure_ad']]
    ]);
  });

  it('does not generate, store or read a nonce when starting a login', async () => {
    const getRandomValues = vi.spyOn(window.crypto, 'getRandomValues');
    const setItem = vi.spyOn(Storage.prototype, 'setItem');
    const getItem = vi.spyOn(Storage.prototype, 'getItem');

    await renderLogin(['keycloak']);
    fireEvent.click(screen.getByRole('link'));

    expect(getRandomValues).not.toHaveBeenCalled();
    expect(setItem).not.toHaveBeenCalled();
    expect(getItem.mock.calls.flat().join(' ')).not.toMatch(/nonce/i);
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });

  it('redeems provider error callbacks so their sensitive URL params are cleared', async () => {
    mocks.location.search = '?state=server-state&error=access_denied';
    mocks.doOAuth.mockResolvedValueOnce(undefined);

    await renderLogin(['keycloak']);

    expect(mocks.doOAuth).toHaveBeenCalledOnce();
  });

  it.each(['?ACCESS_TOKEN=t', '?Refresh_Token=r', '#access_token=t'])(
    'cleans up credentials in %s regardless of key case',
    async raw => {
      if (raw.startsWith('?')) {
        mocks.location.search = raw;
      } else {
        mocks.location.hash = raw;
      }
      mocks.doOAuth.mockResolvedValueOnce(undefined);

      await renderLogin(['keycloak']);

      expect(mocks.doOAuth).toHaveBeenCalledOnce();
    }
  );

  it.each(['#section', '?provider=keycloak'])('does not redeem a URL without callback data (%s)', async raw => {
    if (raw.startsWith('?')) {
      mocks.location.search = raw;
    } else {
      mocks.location.hash = raw;
    }

    await renderLogin(['keycloak']);

    expect(mocks.doOAuth).not.toHaveBeenCalled();
  });
});
