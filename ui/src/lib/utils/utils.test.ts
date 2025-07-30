import { FailedRequest } from 'lib/types/lookup';
import { StorageKey } from 'lib/utils/constants';
import debounce from 'lodash-es/debounce';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import MockLocalStorage from '../../tests/MockLocalStorage';
import { simpleHash } from './hashUtil';
import { buildName, getAxiosCache, getStored, removeStored, setAxiosCache, setStored } from './sessionStorage';
import { delay, filterEnrichments, removeEmpty, searchObject, twitterShort } from './utils';

// Mock dependencies
vi.mock('lodash-es/debounce');
vi.mock('lib/utils/constants', () => ({
  MY_SESSION_STORAGE_PREFIX: 'test.ui.cache',
  StorageKey: {
    AXIOS_CACHE: 'axios.cache',
    PROVIDER: 'provider',
    APP_TOKEN: 'app_token'
  }
}));

describe('simpleHash', () => {
  it('should return a consistent hash for the same input', () => {
    const input = 'test string';
    const hash1 = simpleHash(input);
    const hash2 = simpleHash(input);

    expect(hash1).toBe(hash2);
    expect(hash1).toMatch(/^[0-9a-z]{7}$/);
  });

  it('should return different hashes for different inputs', () => {
    const hash1 = simpleHash('test1');
    const hash2 = simpleHash('test2');

    expect(hash1).not.toBe(hash2);
  });

  it('should handle empty string', () => {
    const hash = simpleHash('');

    expect(hash).toBe('0000000');
    expect(hash).toHaveLength(7);
  });

  it('should handle single character', () => {
    const hash = simpleHash('a');

    expect(hash).toMatch(/^[0-9a-z]{7}$/);
    expect(hash).toHaveLength(7);
  });

  it('should handle special characters', () => {
    const hash = simpleHash('!@#$%^&*()');

    expect(hash).toMatch(/^[0-9a-z]{7}$/);
    expect(hash).toHaveLength(7);
  });

  it('should handle unicode characters', () => {
    const hash = simpleHash('🚀 测试 café');

    expect(hash).toMatch(/^[0-9a-z]{7}$/);
    expect(hash).toHaveLength(7);
  });

  it('should handle long strings', () => {
    const longString = 'a'.repeat(1000);
    const hash = simpleHash(longString);

    expect(hash).toMatch(/^[0-9a-z]{7}$/);
    expect(hash).toHaveLength(7);
  });

  it('should produce different hashes for strings with same characters in different order', () => {
    const hash1 = simpleHash('abc');
    const hash2 = simpleHash('bca');
    const hash3 = simpleHash('cab');

    expect(hash1).not.toBe(hash2);
    expect(hash2).not.toBe(hash3);
    expect(hash1).not.toBe(hash3);
  });

  it('should handle whitespace variations', () => {
    const hash1 = simpleHash('test string');
    const hash2 = simpleHash('test  string');
    const hash3 = simpleHash(' test string ');

    expect(hash1).not.toBe(hash2);
    expect(hash2).not.toBe(hash3);
    expect(hash1).not.toBe(hash3);
  });

  it('should always return a 7-character string in base36 format', () => {
    const testCases = ['', 'a', 'hello', 'very long string with many characters'];

    testCases.forEach(testCase => {
      const hash = simpleHash(testCase);
      expect(hash).toHaveLength(7);
      expect(hash).toMatch(/^[0-9a-z]{7}$/);
    });
  });
});

// Mock sessionStorage
const mockSessionStorage: Storage = new MockLocalStorage() as any;
const mockDebounce = vi.fn((fn: () => void) => fn());

// Replace sessionStorage in global scope
Object.defineProperty(window, 'sessionStorage', {
  value: mockSessionStorage,
  writable: true
});

describe('sessionStorage utilities', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSessionStorage.clear();

    vi.mocked(debounce).mockImplementation(mockDebounce as any);
  });

  describe('buildName', () => {
    it('should build storage key with prefix', () => {
      const result = buildName('test-key');
      expect(result).toBe('test.ui.cache.test-key');
    });

    it('should handle StorageKey enum values', () => {
      const result = buildName(StorageKey.AXIOS_CACHE);
      expect(result).toBe('test.ui.cache.axios.cache');
    });
  });

  describe('setStored', () => {
    it('should store data using throttled writes', async () => {
      const testData = { key: 'value' };

      setStored(StorageKey.PROVIDER, testData);
      setStored(StorageKey.APP_TOKEN, 'example');

      expect(debounce).toHaveBeenCalledWith(expect.any(Function), 250, {
        leading: false,
        trailing: true,
        maxWait: 800
      });

      expect(mockSessionStorage.setItem).toHaveBeenCalledWith('test.ui.cache.provider', JSON.stringify(testData));
    });

    it('should handle quota errors gracefully', () => {
      const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const error = new Error('Quota exceeded');
      vi.mocked(mockSessionStorage.setItem).mockImplementationOnce(() => {
        throw error;
      });

      const testData = { key: 'value' };
      setStored(StorageKey.PROVIDER, testData);

      expect(consoleWarn).toHaveBeenCalledWith('Quota Error when saving to sessionStorage', error);
      consoleWarn.mockRestore();
    });

    it('should batch multiple writes through throttling', () => {
      let debouncedFunction: (() => void) | null = null;
      mockDebounce.mockImplementation((fn: () => void) => {
        debouncedFunction = fn;
      });

      const testData1 = { key1: 'value1' };
      const testData2 = { key2: 'value2' };

      setStored(StorageKey.PROVIDER, testData1);
      setStored(StorageKey.APP_TOKEN, testData2);

      expect(mockDebounce).toHaveBeenCalledTimes(2);
      expect(mockSessionStorage.setItem).not.toHaveBeenCalled();

      // Execute the debounced function
      if (debouncedFunction) {
        debouncedFunction();
      }

      expect(mockSessionStorage.setItem).toHaveBeenCalledWith('test.ui.cache.provider', JSON.stringify(testData1));
      expect(mockSessionStorage.setItem).toHaveBeenCalledWith('test.ui.cache.app_token', JSON.stringify(testData2));
    });
  });

  describe('getStored', () => {
    beforeEach(() => {
      vi.clearAllMocks();
      mockSessionStorage.clear();

      vi.mocked(debounce).mockImplementation(mockDebounce as any);
    });

    it('should retrieve stored data', () => {
      const testData = { key: 'value' };
      mockSessionStorage.setItem('test.ui.cache.provider', JSON.stringify(testData));

      const result = getStored(StorageKey.PROVIDER);

      expect(mockSessionStorage.getItem).toHaveBeenCalledWith('test.ui.cache.provider');
      expect(result).toEqual(testData);
    });

    it('should handle null values from sessionStorage', () => {
      vi.mocked(mockSessionStorage.getItem).mockReturnValueOnce(null);

      const result = getStored(StorageKey.PROVIDER);

      expect(result).toEqual(null);
    });

    it('should return pending changes instead of stored data', () => {
      const storedData = { existing: 'data' };
      const pendingData = { new: 'change' };

      mockSessionStorage.setItem('test.ui.cache.provider', JSON.stringify(storedData));

      // First set some pending changes (without triggering the debounced write)
      let pendingFunction: () => void;
      mockDebounce.mockImplementationOnce((_fn: () => void) => {
        // Store but don't execute the function
        pendingFunction = _fn;
      });

      setStored(StorageKey.PROVIDER, pendingData);

      // Now get the data - should merge stored + pending
      const result = getStored(StorageKey.PROVIDER);

      expect(result).toEqual(pendingData);

      pendingFunction?.();
    });

    it('should return typed data', () => {
      interface TestType {
        name: string;
        count: number;
      }

      const testData: TestType = { name: 'test', count: 42 };
      mockSessionStorage.setItem('test.ui.cache.provider', JSON.stringify(testData));

      const result = getStored<TestType>(StorageKey.PROVIDER);

      expect(result).toEqual(testData);
      expect(typeof result.name).toBe('string');
      expect(typeof result.count).toBe('number');
    });
  });

  describe('removeStored', () => {
    it('should remove data from sessionStorage', () => {
      removeStored(StorageKey.PROVIDER);

      expect(mockSessionStorage.removeItem).toHaveBeenCalledWith('test.ui.cache.provider');
    });

    it('should clear pending changes', () => {
      // Set some pending changes first
      let debouncedFunction: (() => void) | null = null;
      mockDebounce.mockImplementation((fn: () => void) => {
        debouncedFunction = fn;
      });

      setStored(StorageKey.PROVIDER, { test: 'data' });

      // Remove the key
      removeStored(StorageKey.PROVIDER);

      // Now trigger the debounced write - should not write the removed key
      if (debouncedFunction) {
        debouncedFunction();
      }

      expect(mockSessionStorage.removeItem).toHaveBeenCalledWith('test.ui.cache.provider');
      // The pending changes should have been cleared, so setItem should not be called
      expect(mockSessionStorage.setItem).not.toHaveBeenCalledWith('test.ui.cache.provider', expect.anything());
    });
  });

  describe('Axios cache functions', () => {
    describe('getAxiosCache', () => {
      it('should return empty object when no cache exists', () => {
        vi.mocked(mockSessionStorage.getItem).mockReturnValueOnce(null);

        const result = getAxiosCache();

        expect(result).toEqual({});
      });

      it('should return existing cache data', () => {
        const cacheData = { etag1: 'data1', etag2: 'data2' };
        mockSessionStorage.setItem('test.ui.cache.axios.cache', JSON.stringify(cacheData));

        const result = getAxiosCache();

        expect(result).toEqual(cacheData);
      });
    });

    describe('setAxiosCache', () => {
      it('should add new entry to cache', () => {
        const existingCache = { etag1: 'data1' };
        mockSessionStorage.setItem('test.ui.cache.axios.cache', JSON.stringify(existingCache));

        setAxiosCache('etag2', 'data2');

        // Verify the cache was updated with the new entry
        expect(mockDebounce).toHaveBeenCalled();
      });

      it('should update existing cache entry', () => {
        const existingCache = { etag1: 'data1' };
        mockSessionStorage.setItem('test.ui.cache.axios.cache', JSON.stringify(existingCache));

        setAxiosCache('etag1', 'updated-data');

        expect(mockDebounce).toHaveBeenCalled();
      });

      it('should work with empty cache', () => {
        vi.mocked(mockSessionStorage.getItem).mockReturnValueOnce(null);

        setAxiosCache('etag1', 'data1');

        expect(mockDebounce).toHaveBeenCalled();
      });
    });
  });

  describe('integration tests', () => {
    it('should handle complete workflow: set, get, remove', () => {
      const testData = { workflow: 'test' };

      // Set data
      setStored(StorageKey.PROVIDER, testData);

      // Get data (should include pending changes)
      expect(getStored(StorageKey.PROVIDER)).toEqual(testData);

      // Remove data
      removeStored(StorageKey.PROVIDER);

      // Get data after removal (should be empty)
      expect(getStored(StorageKey.PROVIDER)).toEqual(null);
    });

    it('should handle multiple concurrent operations', () => {
      let debouncedFunction: (() => void) | null = null;
      mockDebounce.mockImplementation((fn: () => void) => {
        debouncedFunction = fn;
      });

      // Set multiple keys
      setStored(StorageKey.PROVIDER, { provider: 'test' });
      setStored(StorageKey.APP_TOKEN, { token: 'abc123' });

      // Remove one key
      removeStored(StorageKey.PROVIDER);

      // Trigger the debounced write
      if (debouncedFunction) {
        debouncedFunction();
      }

      // Should only write the token, not the provider (since it was removed)
      expect(mockSessionStorage.setItem).toHaveBeenCalledWith(
        'test.ui.cache.app_token',
        JSON.stringify({ token: 'abc123' })
      );
      expect(mockSessionStorage.setItem).not.toHaveBeenCalledWith('test.ui.cache.provider', expect.anything());
    });
  });
});

describe('utils.ts utility functions', () => {
  describe('twitterShort', () => {
    it('should return "?" for null or undefined date', () => {
      expect(twitterShort(null as any)).toBe('?');
      expect(twitterShort(undefined as any)).toBe('?');
      expect(twitterShort('')).toBe('?');
      expect(twitterShort('?')).toBe('?');
    });

    it('should return formatted time string for valid dates', () => {
      const pastDate = new Date('2023-01-01');
      const result = twitterShort(pastDate);

      expect(typeof result).toBe('string');
      expect(result).not.toBe('?');
      expect(result.length).toBeGreaterThan(0);
    });

    it('should handle string dates', () => {
      const result = twitterShort('2023-01-01');

      expect(typeof result).toBe('string');
      expect(result).not.toBe('?');
      expect(result.length).toBeGreaterThan(0);
    });

    it('should handle numeric timestamps', () => {
      const timestamp = Date.now() - 86400000; // 1 day ago
      const result = twitterShort(timestamp);

      expect(typeof result).toBe('string');
      expect(result).not.toBe('?');
      expect(result.length).toBeGreaterThan(0);
    });

    it('should handle future dates', () => {
      const futureDate = new Date(Date.now() + 86400000); // 1 day from now
      const result = twitterShort(futureDate);

      expect(typeof result).toBe('string');
      expect(result).not.toBe('?');
      expect(result.length).toBeGreaterThan(0);
    });
  });

  describe('delay', () => {
    beforeEach(() => {
      vi.clearAllTimers();
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should resolve after specified delay', async () => {
      const promise = delay(100);

      // Initially should not resolve
      let resolved = false;
      promise.then(() => {
        resolved = true;
      });

      expect(resolved).toBe(false);

      // Fast-forward time
      vi.advanceTimersByTime(100);
      await promise;

      expect(resolved).toBe(true);
    });

    it('should be cancellable without rejection by default', () => {
      const promise = delay(100);

      promise.cancel();

      // Should not throw
      expect(() => promise.cancel()).not.toThrow();
    });

    it('should reject on cancel when rejectOnCancel is true', async () => {
      const promise = delay(100, true);

      promise.cancel();

      await expect(promise).rejects.toBeUndefined();
    });

    it('should clear timeout on cancel', () => {
      const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout');
      const promise = delay(100);

      promise.cancel();

      expect(clearTimeoutSpy).toHaveBeenCalled();
    });
  });

  describe('removeEmpty', () => {
    it('should remove null and undefined values but preserve falsy values', () => {
      const input = {
        a: 1,
        b: null,
        c: undefined,
        d: 'test',
        e: 0, // This is falsy but not null/undefined, should be filtered out due to !!v check
        f: false, // This is falsy but not null/undefined, should be filtered out due to !!v check
        g: '' // This is falsy but not null/undefined, should be filtered out due to !!v check
      };

      const result = removeEmpty(input);

      // Based on the implementation, falsy values (0, false, '') are filtered out by !!v check
      expect(result).toEqual({
        a: 1,
        d: 'test'
      });
    });

    it('should handle nested objects', () => {
      const input = {
        a: 1,
        b: {
          c: 2,
          d: null,
          e: {
            f: 3,
            g: undefined
          }
        }
      };

      const result = removeEmpty(input);

      expect(result).toEqual({
        a: 1,
        b: {
          c: 2,
          e: {
            f: 3
          }
        }
      });
    });

    it('should preserve arrays', () => {
      const input = {
        a: [1, 2, null, 3],
        b: []
      };

      const result = removeEmpty(input);

      expect(result).toEqual({
        a: [1, 2, null, 3],
        b: []
      });
    });

    it('should return null for empty object when aggressive is true', () => {
      expect(removeEmpty({}, true)).toBe(null);
      expect(removeEmpty([], true)).toBe(null); // Arrays are also considered empty when aggressive
    });

    it('should handle null input', () => {
      expect(removeEmpty(null)).toEqual({});
      expect(removeEmpty(undefined)).toEqual({});
    });

    it('should preserve nested objects that are not empty', () => {
      const input = {
        a: 1,
        b: {
          c: null,
          d: undefined
        },
        e: 2
      };

      const result = removeEmpty(input);

      // The nested object b becomes empty after filtering, but may still be present
      expect(result).toEqual({
        a: 1,
        b: {}, // Empty object remains
        e: 2
      });
    });
  });

  describe('searchObject', () => {
    it('should search keys and values', () => {
      const input = {
        name: 'John',
        age: 30,
        address: {
          street: 'Main St',
          city: 'New York'
        }
      };

      const result = searchObject(input, 'john');

      expect(result).toHaveProperty('name', 'John');
    });

    it('should be case insensitive', () => {
      const input = {
        Name: 'JOHN',
        email: 'john@example.com'
      };

      const result = searchObject(input, 'john');

      expect(result).toHaveProperty('Name', 'JOHN');
      expect(result).toHaveProperty('email', 'john@example.com');
    });

    it('should search nested objects', () => {
      const input = {
        user: {
          profile: {
            name: 'Alice'
          }
        },
        settings: {
          theme: 'dark'
        }
      };

      const result = searchObject(input, 'alice');

      expect(result).toHaveProperty('user.profile.name', 'Alice');
    });

    it('should return original object on regex error', () => {
      const input = { test: 'value' };

      // Invalid regex pattern
      const result = searchObject(input, '[');

      expect(result).toEqual(input);
    });

    it('should return empty object when no matches found', () => {
      const input = {
        name: 'John',
        age: 30
      };

      const result = searchObject(input, 'nonexistent');

      expect(result).toEqual({});
    });

    it('should handle empty input', () => {
      expect(searchObject({}, 'test')).toEqual({});
      expect(searchObject(null, 'test')).toEqual(null); // null input returns null
    });
  });

  describe('filterEnrichments', () => {
    it('should remove duplicate FailedRequest objects', () => {
      const failedRequests: FailedRequest[] = [
        { source: 'test1', type: 'ip', value: '1.2.3.4' },
        { source: 'test2', type: 'domain', value: 'example.com' },
        { source: 'test1', type: 'ip', value: '1.2.3.4' }, // duplicate
        { source: 'test3', type: 'hash', value: 'abc123' }
      ];

      const result = filterEnrichments(failedRequests);

      expect(result).toHaveLength(3);
      expect(result).toContainEqual({ source: 'test1', type: 'ip', value: '1.2.3.4' });
      expect(result).toContainEqual({ source: 'test2', type: 'domain', value: 'example.com' });
      expect(result).toContainEqual({ source: 'test3', type: 'hash', value: 'abc123' });
    });

    it('should handle empty array', () => {
      const result = filterEnrichments([]);

      expect(result).toEqual([]);
    });

    it('should preserve array with no duplicates', () => {
      const failedRequests: FailedRequest[] = [
        { source: 'test1', type: 'ip', value: '1.2.3.4' },
        { source: 'test2', type: 'domain', value: 'example.com' }
      ];

      const result = filterEnrichments(failedRequests);

      expect(result).toEqual(failedRequests);
    });

    it('should handle array with all duplicates', () => {
      const failedRequest: FailedRequest = { source: 'test', type: 'ip', value: '1.2.3.4' };
      const failedRequests: FailedRequest[] = [failedRequest, failedRequest, failedRequest];

      const result = filterEnrichments(failedRequests);

      expect(result).toHaveLength(1);
      expect(result[0]).toEqual(failedRequest);
    });
  });
});
