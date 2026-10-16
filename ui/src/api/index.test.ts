import { StorageKey } from 'lib/utils/constants';
import AxiosClient from 'rest/AxiosClient';
import { URLSearchParams } from 'url';
import * as localStorage from 'utils/localStorage';
import * as xsrf from 'utils/xsrf';
import { afterEach, beforeEach, describe, expect, it, Mock, vi } from 'vitest';
import * as oauthLogin from './auth/login';
import { hdelete, hget, hpatch, hpost, hput, joinAllUri, joinParams, joinUri, setHeaders, uri } from './index';

interface MockAxiosClientType {
  fetch: Mock;
}

// Mock dependencies
vi.mock('utils/localStorage');
vi.mock('utils/xsrf');

vi.mock('rest/AxiosClient', () => {
  const MockClient = vi.fn();
  MockClient.prototype.fetch = vi.fn();

  return { default: MockClient };
});

describe('API Index', () => {
  let client: MockAxiosClientType;

  beforeEach(() => {
    client = new AxiosClient() as any;

    vi.mocked(xsrf.default).mockReturnValue('mock-xsrf-token');
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('forwards only allowlisted OAuth callback parameters', async () => {
    const search = new URLSearchParams({
      provider: 'local',
      code: 'local-code',
      state: 'server-state',
      nonce: 'injected-nonce',
      refresh_token: 'injected-refresh',
      id_token: 'injected.id.token',
      access_token: 'injected-access',
      arbitrary: 'value'
    });
    client.fetch.mockResolvedValue([{ api_response: { app_token: 'local-token' } }, 200]);
    const getItem = vi.spyOn(window.localStorage, 'getItem');

    await oauthLogin.get(search);

    const forwarded: URLSearchParams = client.fetch.mock.calls[0][3];
    expect(client.fetch.mock.calls[0][0]).toContain('/auth/login');
    expect(Object.fromEntries(forwarded.entries())).toEqual({
      provider: 'local',
      code: 'local-code',
      state: 'server-state'
    });
    expect(forwarded.toString()).not.toMatch(/injected|nonce|refresh_token|id_token|access_token|arbitrary/);
    expect(getItem).not.toHaveBeenCalled();
    getItem.mockRestore();
  });

  it('does not persist rejected OAuth callback parameters as the next location', async () => {
    const search = new URLSearchParams({ provider: 'local', code: 'local-code', state: 'server-state' });
    client.fetch.mockResolvedValue([{ api_error_message: 'OAuth authentication failed.' }, 401]);

    await oauthLogin.get(search);

    expect(localStorage.setStored).not.toHaveBeenCalled();
  });

  it.each([
    ['/login', '?provider=local&code=c&state=s&id_token=a.b.c', ''],
    ['/login', '', ''],
    ['/fetchers', '?code=c&state=s', ''],
    ['/fetchers', '?refresh_token=attacker', ''],
    ['/fetchers', '', '#access_token=t']
  ])(
    'does not persist %s%s%s when an unrelated request returns 401 on an OAuth callback URL',
    async (pathname, search, hash) => {
      Object.defineProperty(global, 'location', { value: { pathname, search, hash }, writable: true });
      vi.mocked(localStorage.getStored).mockReturnValue(null);
      client.fetch.mockResolvedValue([{ api_error_message: 'Unauthorized' }, 401]);

      await hget('/configs');

      expect(localStorage.setStored).not.toHaveBeenCalledWith(StorageKey.NEXT_LOCATION, expect.anything());
      expect(localStorage.setStored).not.toHaveBeenCalledWith(StorageKey.NEXT_SEARCH, expect.anything());
    }
  );

  describe('joinParams', () => {
    it('should return original URI when no search params provided', () => {
      const result = joinParams('/api/test');
      expect(result).toBe('/api/test');
    });

    it('should append search params with ? when URI has no existing params', () => {
      const params = new URLSearchParams({ key: 'value' });
      const result = joinParams('/api/test', params);
      expect(result).toBe('/api/test?key=value');
    });

    it('should append search params with & when URI already has params', () => {
      const params = new URLSearchParams({ key2: 'value2' });
      const result = joinParams('/api/test?existing=param', params);
      expect(result).toBe('/api/test?existing=param&key2=value2');
    });
  });

  describe('joinUri', () => {
    it('should join two URIs without search params', () => {
      const result = joinUri('/api', 'test');
      expect(result).toBe('/api/v1/api/test');
    });

    it('should join two URIs with search params', () => {
      const params = new URLSearchParams({ key: 'value' });
      const result = joinUri('/api', 'test', params);
      expect(result).toBe('/api/v1/api/test?key=value');
    });
  });

  describe('joinAllUri', () => {
    it('should join multiple URL parts', () => {
      const result = joinAllUri('/api', 'v1', 'test', 'endpoint');
      expect(result).toBe('/api/v1/test/endpoint');
    });

    it('should handle empty parts', () => {
      const result = joinAllUri('/api', '', 'test');
      expect(result).toBe('/api/test');
    });
  });

  describe('setHeaders', () => {
    it('should return empty headers when no ifMatch provided', () => {
      const result = setHeaders();
      expect(result).toEqual({});
    });

    it('should return headers with If-Match when ifMatch provided', () => {
      const result = setHeaders('etag-value');
      expect(result).toEqual({ 'If-Match': 'etag-value' });
    });
  });

  describe('uri', () => {
    it('should return the base API URI', () => {
      const result = uri();
      expect(result).toBe('/api/v1');
    });
  });

  describe('HTTP Methods', () => {
    beforeEach(() => {
      client.fetch.mockResolvedValue([{ api_response: 'test-response' }, 200]);
    });

    describe('hget', () => {
      it('should perform GET request with correct parameters', async () => {
        const params = new URLSearchParams({ test: 'value' });
        const config = { timeout: 5000 };

        const result = await hget('/test', params, config);

        expect(result).toBe('test-response');
        expect(client.fetch).toHaveBeenCalledWith(
          '/api/v1/test',
          'get',
          null,
          params,
          expect.objectContaining({
            timeout: 5000,
            headers: expect.objectContaining({
              'Content-Type': 'application/json',
              'X-XSRF-TOKEN': 'mock-xsrf-token'
            })
          })
        );
      });
    });

    describe('hpost', () => {
      it('should perform POST request with body', async () => {
        const body = { data: 'test' };
        const config = { timeout: 5000 };

        const result = await hpost('/test', body, config);

        expect(result).toBe('test-response');
        expect(client.fetch).toHaveBeenCalledWith(
          '/api/v1/test',
          'post',
          body,
          undefined,
          expect.objectContaining({
            timeout: 5000,
            headers: expect.objectContaining({
              'Content-Type': 'application/json',
              'X-XSRF-TOKEN': 'mock-xsrf-token'
            })
          })
        );
      });
    });

    describe('hput', () => {
      it('should perform PUT request with body', async () => {
        const body = { data: 'test' };

        const result = await hput('/test', body);

        expect(result).toBe('test-response');
        expect(client.fetch).toHaveBeenCalledWith(
          '/api/v1/test',
          'put',
          body,
          undefined,
          expect.objectContaining({
            headers: expect.objectContaining({
              'Content-Type': 'application/json',
              'X-XSRF-TOKEN': 'mock-xsrf-token'
            })
          })
        );
      });
    });

    describe('hpatch', () => {
      it('should perform PATCH request with body', async () => {
        const body = { data: 'test' };

        const result = await hpatch('/test', body);

        expect(result).toBe('test-response');
        expect(client.fetch).toHaveBeenCalledWith(
          '/api/v1/test',
          'patch',
          body,
          undefined,
          expect.objectContaining({
            headers: expect.objectContaining({
              'Content-Type': 'application/json',
              'X-XSRF-TOKEN': 'mock-xsrf-token'
            })
          })
        );
      });
    });

    describe('hdelete', () => {
      it('should perform DELETE request', async () => {
        const result = await hdelete('/test');

        expect(result).toBe('test-response');
        expect(client.fetch).toHaveBeenCalledWith(
          '/api/v1/test',
          'delete',
          null,
          undefined,
          expect.objectContaining({
            headers: expect.objectContaining({
              'Content-Type': 'application/json',
              'X-XSRF-TOKEN': 'mock-xsrf-token'
            })
          })
        );
      });

      it('should perform DELETE request with body', async () => {
        const body = { id: 'test' };

        const result = await hdelete('/test', body);

        expect(result).toBe('test-response');
        expect(client.fetch).toHaveBeenCalledWith(
          '/api/v1/test',
          'delete',
          body,
          undefined,
          expect.objectContaining({
            headers: expect.objectContaining({
              'Content-Type': 'application/json',
              'X-XSRF-TOKEN': 'mock-xsrf-token'
            })
          })
        );
      });
    });
  });

  describe('Authentication handling', () => {
    it('should include Authorization header when token is present', async () => {
      vi.mocked(localStorage.getStored).mockImplementation(key => (key === StorageKey.APP_TOKEN ? 'mock-token' : null));
      client.fetch.mockResolvedValue([{ api_response: 'test-response' }, 200]);

      await hget('/test');

      expect(client.fetch).toHaveBeenCalledWith(
        '/api/v1/test',
        'get',
        null,
        undefined,
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer mock-token'
          })
        })
      );
    });

    it('should not override existing Authorization header', async () => {
      vi.mocked(localStorage.getStored).mockImplementation(key => (key === StorageKey.APP_TOKEN ? 'mock-token' : null));
      client.fetch.mockResolvedValue([{ api_response: 'test-response' }, 200]);

      const config = {
        headers: {
          Authorization: 'Bearer custom-token'
        }
      };

      await hget('/test', undefined, config);

      expect(client.fetch).toHaveBeenCalledWith(
        '/api/v1/test',
        'get',
        null,
        undefined,
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer custom-token'
          })
        })
      );
    });
  });

  describe('Error handling', () => {
    it('should return null when no JSON response', async () => {
      client.fetch.mockResolvedValue([null, 200]);

      const result = await hget('/test');

      expect(result).toBe(null);
    });

    it('should throw error for non-success status codes', async () => {
      client.fetch.mockResolvedValue([{ api_error_message: 'Test error' }, 400]);

      await expect(hget('/test')).rejects.toThrow('Test error');
    });

    it('should handle 304 status as success', async () => {
      client.fetch.mockResolvedValue([{ api_response: 'cached-response' }, 304]);

      const result = await hget('/test');

      expect(result).toBe('cached-response');
    });

    it('should handle 401 status and save location for redirect', async () => {
      client.fetch.mockResolvedValue([{ api_error_message: 'Unauthorized' }, 401]);

      // Mock window.location
      Object.defineProperty(global, 'location', {
        value: {
          pathname: '/current-path',
          search: '?param=value'
        },
        writable: true
      });

      const result = await hget('/test');

      expect(result).toBeUndefined();
      expect(localStorage.setStored).toHaveBeenCalledWith(StorageKey.NEXT_LOCATION, '/current-path');
      expect(localStorage.setStored).toHaveBeenCalledWith(StorageKey.NEXT_SEARCH, '?param=value');
      expect(localStorage.saveLoginCredential).toHaveBeenCalledWith({});
    });
  });

  describe('Token refresh', () => {
    it('should attempt token refresh on 401 when refresh token exists', async () => {
      // Mock the fetch calls
      client.fetch
        .mockResolvedValueOnce([{ api_error_message: 'Unauthorized' }, 401]) // First call fails
        .mockResolvedValueOnce([{ api_response: { access_token: 'new-token' } }, 200]) // Refresh succeeds
        .mockResolvedValueOnce([{ api_response: 'retry-success' }, 200]); // Retry succeeds

      // Mock localStorage for refresh scenario
      vi.mocked(localStorage.getStored).mockImplementation(key => {
        switch (key) {
          case StorageKey.REFRESH_TOKEN:
            return 'mock-refresh-token';
          case StorageKey.PROVIDER:
            return 'mock-provider';
          default:
            return null;
        }
      });

      const result = await hget('/test');

      expect(result).toBe('retry-success');
      expect(client.fetch).toHaveBeenCalledTimes(3);
      expect(client.fetch.mock.calls[1][0]).toBe('/api/v1/auth/refresh');
      expect(client.fetch.mock.calls[1][1]).toBe('post');
      expect(client.fetch.mock.calls[1][2]).toEqual({ provider: 'mock-provider', refresh_token: 'mock-refresh-token' });
      expect(client.fetch.mock.calls[1][3]).toBeUndefined();
      expect(localStorage.saveLoginCredential).toHaveBeenCalledWith({ access_token: 'new-token' });
      expect(localStorage.removeStored).toHaveBeenCalledWith(StorageKey.NEXT_LOCATION);
      expect(localStorage.removeStored).toHaveBeenCalledWith(StorageKey.NEXT_SEARCH);
    });

    it('does not recurse when the refresh request itself is rejected', async () => {
      client.fetch
        .mockResolvedValueOnce([{ api_error_message: 'Unauthorized' }, 401])
        .mockResolvedValueOnce([{ api_error_message: 'Authentication failed.' }, 401]);
      vi.mocked(localStorage.getStored).mockImplementation(key =>
        key === StorageKey.REFRESH_TOKEN ? 'mock-refresh-token' : key === StorageKey.PROVIDER ? 'mock-provider' : null
      );

      const result = await hget('/test');

      expect(result).toBeUndefined();
      expect(client.fetch).toHaveBeenCalledTimes(2);
      expect(localStorage.saveLoginCredential).toHaveBeenCalledWith({});
    });

    it('falls back to re-login when the refresh request is invalid', async () => {
      client.fetch
        .mockResolvedValueOnce([{ api_error_message: 'Unauthorized' }, 401])
        .mockResolvedValueOnce([{ api_error_message: 'Invalid token refresh request.' }, 400]);
      vi.mocked(localStorage.getStored).mockImplementation(key =>
        key === StorageKey.REFRESH_TOKEN ? 'mock-refresh-token' : null
      );

      const result = await hget('/test');

      expect(result).toBeUndefined();
      expect(localStorage.saveLoginCredential).toHaveBeenCalledWith({});
    });
  });
});
