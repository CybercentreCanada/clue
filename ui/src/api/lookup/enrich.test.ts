// Import necessary types and test utilities
import type { AxiosRequestConfig } from 'axios';
import type { Selector } from 'lib/types/lookup';
import cloneDeep from 'lodash-es/cloneDeep';
import set from 'lodash-es/set';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import enrichExample from '../../tests/models/enrich.example.json';
import { post, uri } from './enrich';

// Mock lodash-es
vi.mock('lodash-es/isNil', { spy: true });
vi.mock('api', { spy: true });
vi.mock('api/lookup', { spy: true });

// Import mocked functions for type checking
// eslint-disable-next-line import/first
import { hpost, joinUri } from 'api';
// eslint-disable-next-line import/first
// eslint-disable-next-line import/first
import isNil from 'lodash-es/isNil';

// Test suite for the Enrichment API
// Covers uri and post functions
describe('Enrichment API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Test the uri() function
  describe('uri', () => {
    it('should construct the correct URI for enrich endpoint', () => {
      const result = uri();

      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/lookup', 'enrich');
      expect(result).toBe('/api/v1/lookup/enrich');
    });
  });

  const mockSelector: Selector = {
    type: 'ip',
    value: '127.0.0.1',
    classification: 'TLP:WHITE'
  };

  const mockBulkData: Selector[] = [
    mockSelector,
    {
      type: 'ip',
      value: '127.0.0.2',
      classification: 'TLP:WHITE'
    }
  ];

  const mockResponse = {
    ip: { '127.0.0.1': enrichExample, '127.0.0.2': set(cloneDeep(enrichExample), 'example.value', '127.0.0.2') }
  };

  // Test the post() function
  describe('post', () => {
    it('should call hpost with minimal parameters', async () => {
      const result = await post(mockBulkData);

      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/lookup/enrich', '', null);
      expect(vi.mocked(hpost)).toHaveBeenCalledWith('/api/v1/lookup/enrich', mockBulkData, undefined);
      expect(result).toEqual(mockResponse);
    });

    it('should handle empty sources array', async () => {
      const result = await post(mockBulkData, []);

      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/lookup/enrich', '', null);
      expect(vi.mocked(hpost)).toHaveBeenCalledWith('/api/v1/lookup/enrich', mockBulkData, undefined);
      expect(result).toEqual(mockResponse);
    });

    it('should include sources parameter when sources provided', async () => {
      const sources = ['provider1', 'provider2'];

      // Mock URLSearchParams
      const mockSearchParams = {
        toString: vi.fn(() => 'sources=provider1,provider2')
      };
      global.URLSearchParams = vi.fn(() => mockSearchParams) as any;

      await post(mockBulkData, sources);

      expect(global.URLSearchParams).toHaveBeenCalledWith('sources=provider1,provider2');
      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/lookup/enrich', '', mockSearchParams);
    });

    it('should include classification parameter when provided', async () => {
      const options = { classification: 'TLP:RED' };

      const mockSearchParams = {
        toString: vi.fn(() => 'classification=TLP%3ARED')
      };
      global.URLSearchParams = vi.fn(() => mockSearchParams) as any;

      await post(mockBulkData, [], options);

      expect(global.URLSearchParams).toHaveBeenCalledWith('classification=TLP%3ARED');
      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/lookup/enrich', '', mockSearchParams);
    });

    it('should include timeout parameter when timeout is not nil', async () => {
      const options = { timeout: 30000 };

      const mockSearchParams = {
        toString: vi.fn(() => 'max_timeout=30000')
      };
      global.URLSearchParams = vi.fn(() => mockSearchParams) as any;

      await post(mockBulkData, [], options);

      expect(vi.mocked(isNil)).toHaveBeenCalledWith(30000);
      expect(global.URLSearchParams).toHaveBeenCalledWith('max_timeout=30000');
      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/lookup/enrich', '', mockSearchParams);
    });

    it('should not include timeout parameter when timeout is null', async () => {
      const options = { timeout: null };

      await post(mockBulkData, [], options);

      expect(vi.mocked(isNil)).toHaveBeenCalledWith(null);
      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/lookup/enrich', '', null);
    });

    it('should include includeRaw parameter when true', async () => {
      const options = { includeRaw: true };

      const mockSearchParams = {
        toString: vi.fn(() => 'include_raw=true')
      };
      global.URLSearchParams = vi.fn(() => mockSearchParams) as any;

      await post(mockBulkData, [], options);

      expect(global.URLSearchParams).toHaveBeenCalledWith('include_raw=true');
      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/lookup/enrich', '', mockSearchParams);
    });

    it('should not include includeRaw parameter when false', async () => {
      const options = { includeRaw: false };

      await post(mockBulkData, [], options);

      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/lookup/enrich', '', null);
    });

    it('should include noCache parameter when true', async () => {
      const options = { noCache: true };

      const mockSearchParams = {
        toString: vi.fn(() => 'no_cache=true')
      };
      global.URLSearchParams = vi.fn(() => mockSearchParams) as any;

      await post(mockBulkData, [], options);

      expect(global.URLSearchParams).toHaveBeenCalledWith('no_cache=true');
      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/lookup/enrich', '', mockSearchParams);
    });

    it('should not include noCache parameter when false', async () => {
      const options = { noCache: false };

      await post(mockBulkData, [], options);

      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/lookup/enrich', '', null);
    });

    it('should combine multiple parameters correctly', async () => {
      const sources = ['provider1', 'provider2'];
      const options = {
        classification: 'TLP:GREEN',
        timeout: 15000,
        includeRaw: true,
        noCache: true
      };

      const mockSearchParams = {
        toString: vi.fn(
          () =>
            'sources=provider1,provider2&classification=TLP%3AGREEN&max_timeout=15000&include_raw=true&no_cache=true'
        )
      };
      global.URLSearchParams = vi.fn(() => mockSearchParams) as any;

      await post(mockBulkData, sources, options);

      expect(global.URLSearchParams).toHaveBeenCalledWith(
        'sources=provider1,provider2&classification=TLP%3AGREEN&max_timeout=15000&include_raw=true&no_cache=true'
      );
      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/lookup/enrich', '', mockSearchParams);
    });

    it('should properly encode special characters in classification', async () => {
      const options = { classification: 'TLP:RED/SPECIAL CHARS & SYMBOLS' };

      const mockSearchParams = {
        toString: vi.fn(() => 'classification=TLP%3ARED%2FSPECIAL%20CHARS%20%26%20SYMBOLS')
      };
      global.URLSearchParams = vi.fn(() => mockSearchParams) as any;

      await post(mockBulkData, [], options);

      expect(global.URLSearchParams).toHaveBeenCalledWith('classification=TLP%3ARED%2FSPECIAL%20CHARS%20%26%20SYMBOLS');
    });

    it('should pass axios config to hpost when provided', async () => {
      const config: AxiosRequestConfig = {
        headers: { 'Custom-Header': 'value' },
        timeout: 10000
      };
      await post(mockBulkData, [], {}, config);

      expect(vi.mocked(hpost)).toHaveBeenCalledWith('/api/v1/lookup/enrich', mockBulkData, config);
    });

    it('should handle hpost errors', async () => {
      const error = new Error('Network error');
      vi.mocked(hpost).mockRejectedValueOnce(error);

      await expect(post(mockBulkData)).rejects.toThrow('Network error');
    });

    it('should handle empty bulk data array', async () => {
      const emptyData: Selector[] = [];
      const result = await post(emptyData);

      expect(vi.mocked(hpost)).toHaveBeenCalledWith('/api/v1/lookup/enrich', emptyData, undefined);
      expect(result).toEqual({});
    });

    it('should handle single selector in bulk data', async () => {
      const singleSelector = [mockSelector];
      const result = await post(singleSelector);

      expect(vi.mocked(hpost)).toHaveBeenCalledWith('/api/v1/lookup/enrich', singleSelector, undefined);
      expect(result).toEqual({ ip: { '127.0.0.1': enrichExample } });
    });

    it('should use default options when not provided', async () => {
      await post(mockBulkData);

      // Should not include any optional parameters by default
      expect(vi.mocked(joinUri)).toHaveBeenCalledWith('/api/v1/lookup/enrich', '', null);
    });
  });
});
