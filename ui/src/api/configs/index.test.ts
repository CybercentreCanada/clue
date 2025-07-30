// Import necessary types and test utilities
import type { AxiosRequestConfig } from 'axios';
import { ApiType } from 'lib/types/config';
import { describe, expect, it, vi } from 'vitest';
import exampleClassification from '../../tests/models/classification.example.json';
import { get, uri } from './index';

// Mock the api module functions for isolation
vi.mock('api', { spy: true });

// Import mocked functions for type checking
// eslint-disable-next-line import/first
import { hget, joinUri } from 'api';

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

      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1', 'configs');
      expect(result).toBe('/api/v1/configs');
    });
  });

  // Test the get() function
  describe('get', () => {
    const mockResponse: ApiType = {
      configuration: {
        auth: {
          oauth_providers: []
        },
        system: {
          version: '1.0.0',
          branch: 'develop',
          commit: 'abcd1234'
        },
        ui: {
          apps: []
        }
      },
      c12nDef: exampleClassification
    };

    it('should call hget with correct parameters when no config provided', async () => {
      const result = await get();

      expect(vi.mocked(hget)).toHaveBeenCalledWith('/api/v1/configs', null, undefined);
      expect(result).toEqual(mockResponse);
    });

    it('should call hget with provided config', async () => {
      const config: AxiosRequestConfig = { timeout: 5000 };

      const result = await get(config);

      expect(vi.mocked(hget)).toHaveBeenCalledWith('/api/v1/configs', null, config);
      expect(result).toEqual(mockResponse);
    });

    it('should handle hget errors', async () => {
      const error = new Error('Network error');
      vi.mocked(hget).mockRejectedValue(error);

      await expect(get()).rejects.toThrow('Network error');
    });
  });
});
