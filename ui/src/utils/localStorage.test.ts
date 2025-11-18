import { LoginResponse } from 'api/auth/login';
import { MY_LOCAL_STORAGE_PREFIX, StorageKey } from 'lib/utils/constants';
import { ClueUser } from 'models/entities/ClueUser';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import MockLocalStorage from '../tests/MockLocalStorage';
import { buildName, getStored, removeStored, saveLoginCredential, setStored } from './localStorage';

// Mock localStorage
const mockLocalStorage: Storage = new MockLocalStorage() as any;
Object.defineProperty(global, 'localStorage', {
  value: mockLocalStorage,
  writable: true
});

describe('localStorage utilities', () => {
  beforeEach(() => {
    mockLocalStorage.clear();
    vi.clearAllMocks();
  });

  describe('buildName', () => {
    it('should build prefixed key name with StorageKey', () => {
      const result = buildName(StorageKey.APP_TOKEN);
      expect(result).toBe(`${MY_LOCAL_STORAGE_PREFIX}.app_token`);
    });

    it('should build prefixed key name with undefined key', () => {
      const result = buildName(undefined);
      expect(result).toBe(`${MY_LOCAL_STORAGE_PREFIX}.undefined`);
    });

    it('should build prefixed key name with PROVIDER key', () => {
      const result = buildName(StorageKey.PROVIDER);
      expect(result).toBe(`${MY_LOCAL_STORAGE_PREFIX}.provider`);
    });

    it('should build prefixed key name with REFRESH_TOKEN key', () => {
      const result = buildName(StorageKey.REFRESH_TOKEN);
      expect(result).toBe(`${MY_LOCAL_STORAGE_PREFIX}.refresh_token`);
    });

    it('should build prefixed key name with AXIOS_CACHE key', () => {
      const result = buildName(StorageKey.AXIOS_CACHE);
      expect(result).toBe(`${MY_LOCAL_STORAGE_PREFIX}.axios.cache`);
    });
  });

  describe('setStored', () => {
    it('should store string value with JSON.stringify', () => {
      const value = 'test-value';
      setStored(StorageKey.APP_TOKEN, value);

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.app_token`,
        JSON.stringify(value)
      );
    });

    it('should store object value with JSON.stringify', () => {
      const value = { key: 'value', nested: { prop: 123 } };
      setStored(StorageKey.AXIOS_CACHE, value);

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.axios.cache`,
        JSON.stringify(value)
      );
    });

    it('should store array value with JSON.stringify', () => {
      const value = ['item1', 'item2', 'item3'];
      setStored(StorageKey.PROVIDER, value);

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.provider`,
        JSON.stringify(value)
      );
    });

    it('should store boolean value with JSON.stringify', () => {
      const value = true;
      setStored(StorageKey.APP_TOKEN, value);

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.app_token`,
        JSON.stringify(value)
      );
    });

    it('should store null value with JSON.stringify', () => {
      const value = null;
      setStored(StorageKey.APP_TOKEN, value);

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.app_token`,
        JSON.stringify(value)
      );
    });
  });

  describe('removeStored', () => {
    it('should remove item from localStorage', () => {
      removeStored(StorageKey.APP_TOKEN);

      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.app_token`);
    });

    it('should remove REFRESH_TOKEN from localStorage', () => {
      removeStored(StorageKey.REFRESH_TOKEN);

      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.refresh_token`);
    });

    it('should remove PROVIDER from localStorage', () => {
      removeStored(StorageKey.PROVIDER);

      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.provider`);
    });

    it('should handle undefined key', () => {
      removeStored(undefined);

      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.undefined`);
    });
  });

  describe('getStored', () => {
    it('should retrieve and parse JSON string value', () => {
      const value = 'test-value';
      vi.mocked(mockLocalStorage.getItem).mockReturnValue(JSON.stringify(value));

      const result = getStored(StorageKey.APP_TOKEN);

      expect(mockLocalStorage.getItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.app_token`);
      expect(result).toBe(value);
    });

    it('should retrieve and parse JSON object value', () => {
      const value = { key: 'value', nested: { prop: 123 } };
      vi.mocked(mockLocalStorage.getItem).mockReturnValue(JSON.stringify(value));

      const result = getStored(StorageKey.AXIOS_CACHE);

      expect(mockLocalStorage.getItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.axios.cache`);
      expect(result).toEqual(value);
    });

    it('should retrieve and parse JSON array value', () => {
      const value = ['item1', 'item2', 'item3'];
      vi.mocked(mockLocalStorage.getItem).mockReturnValue(JSON.stringify(value));

      const result = getStored<string[]>(StorageKey.PROVIDER);

      expect(mockLocalStorage.getItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.provider`);
      expect(result).toEqual(value);
    });

    it('should retrieve and parse JSON boolean value', () => {
      const value = false;
      vi.mocked(mockLocalStorage.getItem).mockReturnValue(JSON.stringify(value));

      const result = getStored<boolean>(StorageKey.APP_TOKEN);

      expect(mockLocalStorage.getItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.app_token`);
      expect(result).toBe(value);
    });

    it('should retrieve and parse null value', () => {
      vi.mocked(mockLocalStorage.getItem).mockReturnValue(JSON.stringify(null));

      const result = getStored(StorageKey.APP_TOKEN);

      expect(mockLocalStorage.getItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.app_token`);
      expect(result).toBe(null);
    });

    it('should handle non-JSON legacy values (migration case)', () => {
      const legacyValue = 'plain-string-not-json';
      vi.mocked(mockLocalStorage.getItem).mockReturnValue(legacyValue);

      const result = getStored(StorageKey.APP_TOKEN);

      expect(mockLocalStorage.getItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.app_token`);
      expect(result).toBe(legacyValue);
    });

    it('should handle null return from localStorage.getItem', () => {
      vi.mocked(mockLocalStorage.getItem).mockReturnValue(null);

      const result = getStored(StorageKey.APP_TOKEN);

      expect(mockLocalStorage.getItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.app_token`);
      expect(result).toBe(null);
    });

    it('should handle invalid JSON gracefully (migration case)', () => {
      const invalidJson = '{invalid json}';
      vi.mocked(mockLocalStorage.getItem).mockReturnValue(invalidJson);

      const result = getStored(StorageKey.APP_TOKEN);

      expect(mockLocalStorage.getItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.app_token`);
      expect(result).toBe(invalidJson);
    });

    it('should work with typed generics', () => {
      interface TestType {
        id: number;
        name: string;
      }

      const value: TestType = { id: 1, name: 'test' };
      vi.mocked(mockLocalStorage.getItem).mockReturnValue(JSON.stringify(value));

      const result = getStored<TestType>(StorageKey.AXIOS_CACHE);

      expect(result).toEqual(value);
      expect(typeof result.id).toBe('number');
      expect(typeof result.name).toBe('string');
    });
  });

  describe('saveLoginCredential', () => {
    const mockUser: ClueUser = {
      username: 'testuser',
      email: 'test@example.com',
      name: 'Test User',
      is_admin: false
    } as any;

    it('should save complete login credentials and return true', () => {
      const loginResponse: LoginResponse = {
        app_token: 'test-app-token',
        refresh_token: 'test-refresh-token',
        provider: 'test-provider',
        user: mockUser
      };

      const result = saveLoginCredential(loginResponse);

      expect(result).toBe(true);
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.app_token`,
        JSON.stringify('test-app-token')
      );
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.refresh_token`,
        JSON.stringify('test-refresh-token')
      );
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.provider`,
        JSON.stringify('test-provider')
      );
    });

    it('should save app_token only when refresh_token is missing', () => {
      const loginResponse: LoginResponse = {
        app_token: 'test-app-token',
        user: mockUser
      };

      const result = saveLoginCredential(loginResponse);

      expect(result).toBe(true);
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.app_token`,
        JSON.stringify('test-app-token')
      );
      expect(mockLocalStorage.setItem).not.toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.refresh_token`,
        expect.anything()
      );
      expect(mockLocalStorage.setItem).not.toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.provider`,
        expect.anything()
      );
    });

    it('should clear tokens and return false when app_token is missing', () => {
      const loginResponse: LoginResponse = {
        refresh_token: 'test-refresh-token',
        provider: 'test-provider',
        user: mockUser
      };

      const result = saveLoginCredential(loginResponse);

      expect(result).toBe(false);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.refresh_token`);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.app_token`);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.provider`);
    });

    it('should clear tokens and return false when app_token is empty string', () => {
      const loginResponse: LoginResponse = {
        app_token: '',
        refresh_token: 'test-refresh-token',
        provider: 'test-provider',
        user: mockUser
      };

      const result = saveLoginCredential(loginResponse);

      expect(result).toBe(false);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.refresh_token`);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.app_token`);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.provider`);
    });

    it('should clear tokens and return false when loginResponse is empty object', () => {
      const loginResponse: LoginResponse = {};

      const result = saveLoginCredential(loginResponse);

      expect(result).toBe(false);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.refresh_token`);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.app_token`);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.provider`);
    });

    it('should handle undefined loginResponse', () => {
      const result = saveLoginCredential(undefined as any);

      expect(result).toBe(false);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.refresh_token`);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.app_token`);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.provider`);
    });

    it('should handle null loginResponse', () => {
      const result = saveLoginCredential(null as any);

      expect(result).toBe(false);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.refresh_token`);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.app_token`);
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.provider`);
    });

    it('should save credentials with provider but no refresh_token', () => {
      const loginResponse: LoginResponse = {
        app_token: 'test-app-token',
        provider: 'test-provider',
        user: mockUser
      };

      const result = saveLoginCredential(loginResponse);

      expect(result).toBe(true);
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.app_token`,
        JSON.stringify('test-app-token')
      );
      expect(mockLocalStorage.setItem).not.toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.refresh_token`,
        expect.anything()
      );
      expect(mockLocalStorage.setItem).not.toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.provider`,
        expect.anything()
      );
    });

    it('should save credentials with refresh_token but no provider', () => {
      const loginResponse: LoginResponse = {
        app_token: 'test-app-token',
        refresh_token: 'test-refresh-token',
        user: mockUser
      };

      const result = saveLoginCredential(loginResponse);

      expect(result).toBe(true);
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.app_token`,
        JSON.stringify('test-app-token')
      );
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.refresh_token`,
        JSON.stringify('test-refresh-token')
      );
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.provider`,
        JSON.stringify(undefined)
      );
    });
  });
});
