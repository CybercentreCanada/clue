// Import necessary types and test utilities
import type { AxiosRequestConfig } from 'axios';
import type { ActionDefinitionsResponse, ActionResult } from 'lib/types/action';
import type { Selector } from 'lib/types/lookup';
import { describe, expect, it, vi } from 'vitest';
import { get, post, uri } from './index';

// Mock the api module functions for isolation
vi.mock('api', { spy: true });

// Import mocked functions for type checking
// eslint-disable-next-line import/first
import { hget, hpost, joinAllUri, joinUri } from 'api';

// Test suite for the Fetchers API
// Covers uri, get, and post functions

describe('Fetchers API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Test the uri() function
  describe('uri', () => {
    it('should construct the correct URI for fetchers endpoint', () => {
      const result = uri();

      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1', 'fetchers');
      expect(result).toBe('/api/v1/fetchers');
    });
  });

  // Test the get() function
  describe('get', () => {
    it('should call hget with correct parameters when no config provided', async () => {
      const mockResponse: ActionDefinitionsResponse = {
        'test.fetcher': {
          id: 'test.fetcher',
          name: 'Test Action',
          classification: 'TLP:WHITE',
          params: { type: 'object', properties: {} }
        }
      };

      vi.mocked(hget).mockResolvedValue(mockResponse);

      const result = await get();

      expect(vi.mocked(hget)).toHaveBeenCalledWith('/api/v1/fetchers', null, undefined);
      expect(result).toEqual(mockResponse);
    });

    it('should call hget with provided config', async () => {
      const config: AxiosRequestConfig = { timeout: 5000 };
      const mockResponse: ActionDefinitionsResponse = {
        'custom.fetcher': {
          id: 'custom.fetcher',
          name: 'Custom Action',
          classification: 'TLP:GREEN',
          params: { type: 'object', properties: { param1: { type: 'string' } } }
        }
      };

      vi.mocked(hget).mockResolvedValue(mockResponse);

      const result = await get(config);

      expect(vi.mocked(hget)).toHaveBeenCalledWith('/api/v1/fetchers', null, config);
      expect(result).toEqual(mockResponse);
    });

    it('should handle hget errors', async () => {
      const error = new Error('Network error');
      vi.mocked(hget).mockRejectedValue(error);

      await expect(get()).rejects.toThrow('Network error');
    });
  });

  // Test the post() function
  describe('post', () => {
    const mockSelector: Selector = {
      type: 'ip',
      value: '192.168.1.1',
      classification: 'TLP:WHITE'
    };

    it('should call hpost with single selector', async () => {
      const mockResult: ActionResult = {
        outcome: 'success',
        summary: 'Action completed successfully'
      };

      vi.mocked(hpost).mockResolvedValue(mockResult);

      const result = await post('test.fetcher', mockSelector);

      expect(vi.mocked(joinAllUri)).toHaveBeenCalledWith('/api/v1/fetchers', 'test/fetcher');
      expect(vi.mocked(hpost)).toHaveBeenCalledWith('/api/v1/fetchers/test/fetcher', mockSelector, undefined);
      expect(result).toEqual(mockResult);
    });

    it('should pass axios config to hpost', async () => {
      const config: AxiosRequestConfig = {
        headers: { 'Custom-Header': 'value' },
        timeout: 10000
      };
      const mockResult: ActionResult = { outcome: 'success' };
      vi.mocked(hpost).mockResolvedValue(mockResult);

      await post('config.fetcher', mockSelector, config);

      expect(vi.mocked(hpost)).toHaveBeenCalledWith('/api/v1/fetchers/config/fetcher', mockSelector, config);
    });

    it('should handle fetcher IDs with dots correctly', async () => {
      const mockResult: ActionResult = { outcome: 'success' };
      vi.mocked(hpost).mockResolvedValue(mockResult);

      await post('category.fetcher', mockSelector);

      expect(vi.mocked(joinAllUri)).toHaveBeenCalledWith('/api/v1/fetchers', 'category/fetcher');
    });

    it('should handle hpost errors', async () => {
      const error = new Error('Server error');
      vi.mocked(hpost).mockRejectedValue(error);

      await expect(post('error.fetcher', mockSelector)).rejects.toThrow('Server error');
    });

    it('should handle failure outcome in response', async () => {
      const mockResult: ActionResult = {
        outcome: 'failure',
        summary: 'Action failed due to invalid parameters'
      };
      vi.mocked(hpost).mockResolvedValue(mockResult);

      const result = await post('failing.fetcher', mockSelector);

      expect(result).toEqual(mockResult);
      expect(result.outcome).toBe('failure');
    });
  });
});
