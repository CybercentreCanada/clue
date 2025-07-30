// Import necessary types and test utilities
import { hget, joinUri } from 'api';
import type { AxiosRequestConfig } from 'axios';
import { describe, expect, it, vi } from 'vitest';
import { get, uri } from './types_detection';

// Mock the api module functions for isolation
vi.mock('api', { spy: true });

// Test suite for the Configs API
// Covers uri, get, and post functions

describe('Configs API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Test the uri() function
  describe('uri', () => {
    it('should construct the correct URI for configs endpoint', () => {
      const result = uri();

      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/lookup', 'types_detection');
      expect(result).toBe('/api/v1/lookup/types_detection');
    });
  });

  // Test the get() function
  describe('get', () => {
    it('should call hget with correct parameters when no config provided', async () => {
      const result = await get();

      expect(vi.mocked(hget)).toHaveBeenCalledWith('/api/v1/lookup/types_detection', null, undefined);
      expect(result).toEqual({
        ip: '^[0-9\\.]+$',
        sha256: '[a-z]{4,64}'
      });
    });

    it('should call hget with provided config', async () => {
      const config: AxiosRequestConfig = { timeout: 5000 };

      const result = await get(config);

      expect(vi.mocked(hget)).toHaveBeenCalledWith('/api/v1/lookup/types_detection', null, config);
      expect(result).toEqual({
        ip: '^[0-9\\.]+$',
        sha256: '[a-z]{4,64}'
      });
    });

    it('should handle hget errors', async () => {
      const error = new Error('Network error');
      vi.mocked(hget).mockRejectedValue(error);

      await expect(get()).rejects.toThrow('Network error');
    });
  });
});
