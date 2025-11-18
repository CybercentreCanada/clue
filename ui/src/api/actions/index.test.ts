// Import necessary types and test utilities
import { hget, hpost, joinUri } from 'api';
import type { AxiosRequestConfig } from 'axios';
import type { ActionDefinitionsResponse, ActionResult } from 'lib/types/action';
import type { Selector } from 'lib/types/lookup';
import { describe, expect, it, vi } from 'vitest';
import { get, post, uri } from './index';

// Mock the api module functions for isolation
vi.mock('api', { spy: true });

// Import mocked functions for type checking
// eslint-disable-next-line import/first

// Test suite for the Actions API
// Covers uri, get, and post functions

describe('Actions API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Test the uri() function
  describe('uri', () => {
    it('should construct the correct URI for actions endpoint', () => {
      const result = uri();

      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1', 'actions');
      expect(result).toBe('/api/v1/actions');
    });
  });

  // Test the get() function
  describe('get', () => {
    it('should call hget with correct parameters when no config provided', async () => {
      const mockResponse: ActionDefinitionsResponse = {
        'test.action': {
          id: 'test.action',
          name: 'Test Action',
          classification: 'TLP:WHITE',
          params: { type: 'object', properties: {} }
        }
      };

      vi.mocked(hget).mockResolvedValue(mockResponse);

      const result = await get();

      expect(vi.mocked(hget)).toHaveBeenCalledWith('/api/v1/actions', null, undefined);
      expect(result).toEqual(mockResponse);
    });

    it('should call hget with provided config', async () => {
      const config: AxiosRequestConfig = { timeout: 5000 };
      const mockResponse: ActionDefinitionsResponse = {
        'custom.action': {
          id: 'custom.action',
          name: 'Custom Action',
          classification: 'TLP:GREEN',
          params: { type: 'object', properties: { param1: { type: 'string' } } }
        }
      };

      vi.mocked(hget).mockResolvedValue(mockResponse);

      const result = await get(config);

      expect(vi.mocked(hget)).toHaveBeenCalledWith('/api/v1/actions', null, config);
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

    const mockParams = { param1: 'value1', param2: 'value2' };

    beforeEach(() => {
      // Setup joinUri to handle the execute path construction
      vi.mocked(joinUri).mockImplementation((...parts) => {
        return parts.filter(part => part !== null).join('/');
      });
    });

    it('should call hpost with single selector and no timeout', async () => {
      const mockResult: ActionResult = {
        outcome: 'success',
        summary: 'Action completed successfully'
      };

      vi.mocked(hpost).mockResolvedValue(mockResult);

      const result = await post('test.action', mockSelector, mockParams);

      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/actions/execute', 'test/action', null);
      expect(vi.mocked(hpost)).toHaveBeenCalledWith(
        '/api/v1/actions/execute/test/action',
        {
          ...mockParams,
          selector: mockSelector,
          selectors: []
        },
        undefined
      );
      expect(result).toEqual(mockResult);
    });

    it('should handle single selector in array format', async () => {
      const mockResult: ActionResult = {
        outcome: 'success',
        output: { data: 'test' }
      };

      vi.mocked(hpost).mockResolvedValue(mockResult);

      const result = await post('my.action', [mockSelector], mockParams);

      expect(vi.mocked(hpost)).toHaveBeenCalledWith(
        '/api/v1/actions/execute/my/action',
        {
          ...mockParams,
          selector: mockSelector,
          selectors: []
        },
        undefined
      );
      expect(result).toEqual(mockResult);
    });

    it('should handle multiple selectors', async () => {
      const selector2: Selector = {
        type: 'domain',
        value: 'example.com',
        classification: 'TLP:GREEN'
      };
      const multipleSelectors = [mockSelector, selector2];

      const mockResult: ActionResult = {
        outcome: 'success',
        summary: 'Bulk action completed'
      };

      vi.mocked(hpost).mockResolvedValue(mockResult);

      const result = await post('bulk.action', multipleSelectors, mockParams);

      expect(vi.mocked(hpost)).toHaveBeenCalledWith(
        '/api/v1/actions/execute/bulk/action',
        {
          ...mockParams,
          selectors: multipleSelectors
        },
        undefined
      );
      expect(result).toEqual(mockResult);
    });

    it('should include timeout parameter when provided', async () => {
      const mockResult: ActionResult = { outcome: 'success' };
      vi.mocked(hpost).mockResolvedValue(mockResult);

      // Mock URLSearchParams constructor and toString
      const mockSearchParams = {
        toString: vi.fn(() => 'max_timeout=30000')
      };
      global.URLSearchParams = vi.fn(() => mockSearchParams) as any;

      await post('timeout.action', mockSelector, mockParams, { timeout: 30000 });

      expect(global.URLSearchParams).toHaveBeenCalledWith('max_timeout=30000');
      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/actions/execute', 'timeout/action', mockSearchParams);
    });

    it('should not include timeout parameter when timeout is null', async () => {
      const mockResult: ActionResult = { outcome: 'success' };
      vi.mocked(hpost).mockResolvedValue(mockResult);

      await post('no-timeout.action', mockSelector, mockParams, { timeout: null });

      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/actions/execute', 'no-timeout/action', null);
    });

    it('should pass axios config to hpost', async () => {
      const config: AxiosRequestConfig = {
        headers: { 'Custom-Header': 'value' },
        timeout: 10000
      };
      const mockResult: ActionResult = { outcome: 'success' };
      vi.mocked(hpost).mockResolvedValue(mockResult);

      await post('config.action', mockSelector, mockParams, {}, config);

      expect(vi.mocked(hpost)).toHaveBeenCalledWith(expect.any(String), expect.any(Object), config);
    });

    it('should handle action IDs with dots correctly', async () => {
      const mockResult: ActionResult = { outcome: 'success' };
      vi.mocked(hpost).mockResolvedValue(mockResult);

      await post('category.action', mockSelector, mockParams);

      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/actions/execute', 'category/action', null);
    });

    it('should handle hpost errors', async () => {
      const error = new Error('Server error');
      vi.mocked(hpost).mockRejectedValue(error);

      await expect(post('error.action', mockSelector, mockParams)).rejects.toThrow('Server error');
    });

    it('should handle failure outcome in response', async () => {
      const mockResult: ActionResult = {
        outcome: 'failure',
        summary: 'Action failed due to invalid parameters'
      };
      vi.mocked(hpost).mockResolvedValue(mockResult);

      const result = await post('failing.action', mockSelector, mockParams);

      expect(result).toEqual(mockResult);
      expect(result.outcome).toBe('failure');
    });
  });
});
