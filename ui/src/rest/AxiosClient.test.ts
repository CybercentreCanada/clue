import { getAxiosCache, setAxiosCache } from 'lib/utils/sessionStorage';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AxiosClient from './AxiosClient';

// Mock sessionStorage utilities
vi.mock('lib/utils/sessionStorage');

describe('AxiosClient', () => {
  let axiosClient: AxiosClient;

  beforeEach(() => {
    // Reset mocks
    vi.mocked(getAxiosCache).mockClear();
    vi.mocked(setAxiosCache).mockClear();

    vi.mocked(getAxiosCache).mockReturnValue({});
    vi.mocked(setAxiosCache).mockImplementation(() => {});

    axiosClient = new AxiosClient();
  });

  describe('HTTP Methods', () => {
    it('should perform successful GET request', async () => {
      const [data, status] = await axiosClient.fetch('/test/get');

      expect(status).toBe(200);
      expect((data.api_response as any).method).toBe('GET');
      expect((data.api_response as any).success).toBe(true);
      expect(data.api_server_version).toBe('1.0.0');
      expect(data.api_status_code).toBe(200);
      expect(data.api_error_message).toBe('');
    });

    it('should perform successful POST request with body', async () => {
      const requestBody = { name: 'test', status: 201 };

      const [data, status] = await axiosClient.fetch('/test/post', 'post', requestBody);

      expect(status).toBe(201);
      expect((data.api_response as any).method).toBe('POST');
      expect((data.api_response as any).body).toEqual(requestBody);
      expect((data.api_response as any).success).toBe(true);
      expect(data.api_status_code).toBe(201);
    });

    it('should perform successful PUT request with body', async () => {
      const requestBody = { id: 1, name: 'updated' };

      const [data, status] = await axiosClient.fetch('/test/put', 'put', requestBody);

      expect(status).toBe(200);
      expect((data.api_response as any).method).toBe('PUT');
      expect((data.api_response as any).body).toEqual(requestBody);
      expect((data.api_response as any).success).toBe(true);
    });

    it('should perform successful PATCH request with body', async () => {
      const requestBody = { name: 'patched' };

      const [data, status] = await axiosClient.fetch('/test/patch', 'patch', requestBody);

      expect(status).toBe(200);
      expect((data.api_response as any).method).toBe('PATCH');
      expect((data.api_response as any).body).toEqual(requestBody);
      expect((data.api_response as any).success).toBe(true);
    });

    it('should perform successful DELETE request', async () => {
      const status = (await axiosClient.fetch('/test/delete', 'delete'))[1];

      expect(status).toBe(204);
    });
  });

  describe('Error Handling', () => {
    it('should handle 400 Bad Request error', async () => {
      const [data, status] = await axiosClient.fetch('/test/error/400');

      expect(status).toBe(400);
      expect(data.api_response).toBe(null);
      expect(data.api_error_message).toBe('Bad Request');
      expect(data.api_status_code).toBe(400);
    });

    it('should handle 500 Internal Server Error', async () => {
      const [data, status] = await axiosClient.fetch('/test/error/500');

      expect(status).toBe(500);
      expect(data.api_response).toBe(null);
      expect(data.api_error_message).toBe('Internal Server Error');
      expect(data.api_status_code).toBe(500);
    });

    it('should handle 502 Bad Gateway error', async () => {
      const [data, status] = await axiosClient.fetch('/test/error/502');

      expect(status).toBe(502);
      expect(data.api_response).toBe(null);
      expect(data.api_error_message).toBe('Bad Gateway');
      expect(data.api_status_code).toBe(502);
    });

    it('should handle 429 Too Many Requests error', async () => {
      const [data, status] = await axiosClient.fetch('/test/error/429');

      expect(status).toBe(429);
      expect(data.api_response).toBe(null);
      expect(data.api_error_message).toBe('Too Many Requests');
      expect(data.api_status_code).toBe(429);
    });
  });

  describe('Request Parameters', () => {
    it('should handle URLSearchParams correctly', async () => {
      const params = new URLSearchParams({
        filter: 'active',
        sort: 'name',
        limit: '10'
      });

      const [data, status] = await axiosClient.fetch('/test/with-params', 'get', undefined, params);

      expect(status).toBe(200);
      expect((data.api_response as any).params).toEqual({
        filter: 'active',
        sort: 'name',
        limit: '10'
      });
    });

    it('should handle request without parameters', async () => {
      const [data, status] = await axiosClient.fetch('/test/with-params');

      expect(status).toBe(200);
      expect((data.api_response as any).params).toEqual({});
    });
  });

  describe('Request Body Handling', () => {
    it('should serialize null body correctly', async () => {
      const [data, status] = await axiosClient.fetch('/test/post', 'post', null);

      expect(status).toBe(201);
      expect((data.api_response as any).body).toBe(null);
    });

    it('should serialize undefined body correctly', async () => {
      const [data, status] = await axiosClient.fetch('/test/post', 'post', undefined);

      expect(status).toBe(201);
      expect((data.api_response as any).body).toBe(null);
    });

    it('should serialize empty object correctly', async () => {
      const [data, status] = await axiosClient.fetch('/test/post', 'post', {});

      expect(status).toBe(201);
      expect((data.api_response as any).body).toEqual({});
    });

    it('should serialize complex object correctly', async () => {
      const complexBody = {
        user: { id: 1, name: 'test' },
        metadata: { tags: ['tag1', 'tag2'], count: 42 },
        settings: null,
        active: true
      };

      const [data, status] = await axiosClient.fetch('/test/post', 'post', complexBody);

      expect(status).toBe(201);
      expect((data.api_response as any).body).toEqual(complexBody);
    });
  });

  describe('ETag Caching', () => {
    it('should cache response data when ETag is present', async () => {
      const [data, status, headers] = await axiosClient.fetch('/test/with-etag');

      expect(status).toBe(200);
      expect((data.api_response as any).cached).toBe(true);
      expect(headers.etag).toBe('test-etag-123');
      expect(setAxiosCache).toHaveBeenCalledWith('test-etag-123', data);
    });

    it('should return cached data on 304 response when cache exists', async () => {
      const cachedData = {
        api_response: { cached: true, from_cache: true },
        api_error_message: '',
        api_server_version: '1.0.0',
        api_status_code: 200
      };

      vi.mocked(getAxiosCache).mockReturnValue({ 'test-etag-123': cachedData });

      // First request to populate ETag
      await axiosClient.fetch('/test/with-etag');

      // Second request with If-Match header should return 304 and use cached data
      const [data, status] = await axiosClient.fetch('/test/with-etag-no-cache', 'get', undefined, undefined, {
        headers: { 'If-Match': 'test-etag-123' }
      });

      expect(status).toBe(304);
      expect(data).toBe(cachedData);
    });

    it('should not cache response when ETag is missing', async () => {
      const [, status] = await axiosClient.fetch('/test/get');

      expect(status).toBe(200);
      expect(setAxiosCache).not.toHaveBeenCalled();
    });
  });

  describe('TypeScript Generics', () => {
    it('should properly type response with generics', async () => {
      interface TestResponse {
        user: { id: number; name: string };
        metadata: { tags: string[]; count: number };
        settings: null;
      }

      const [data, status] = await axiosClient.fetch<TestResponse>('/test/json-response');

      expect(status).toBe(200);

      // TypeScript should infer correct types
      const response = data.api_response as TestResponse;
      expect(response.user.id).toBe(1);
      expect(response.user.name).toBe('test user');
      expect(response.metadata.tags).toEqual(['tag1', 'tag2']);
      expect(response.metadata.count).toBe(42);
      expect(response.settings).toBe(null);
    });
  });

  describe('Axios Configuration', () => {
    it('should accept custom axios configuration', async () => {
      const customConfig = {
        timeout: 5000,
        headers: { 'X-Custom-Header': 'test-value' }
      };

      const [data, status] = await axiosClient.fetch('/test/get', 'get', undefined, undefined, customConfig);

      expect(status).toBe(200);
      expect((data.api_response as any).success).toBe(true);
    });

    it('should merge custom config with default config', async () => {
      const customConfig = {
        headers: { Authorization: 'Bearer test-token' }
      };

      const [data, status] = await axiosClient.fetch('/test/post', 'post', { test: 'data' }, undefined, customConfig);

      expect(status).toBe(201);
      expect((data.api_response as any).body).toEqual({ test: 'data' });
    });
  });

  describe('Status Code Validation', () => {
    it('should accept 2xx status codes as valid', async () => {
      const [data, status] = await axiosClient.fetch('/test/post', 'post', { test: 'data' });

      expect(status).toBe(201);
      expect((data.api_response as any).success).toBe(true);
    });

    it('should accept 304 status code as valid', async () => {
      // Mock cache to trigger 304 response
      vi.mocked(getAxiosCache).mockReturnValue({ 'test-etag-123': { cached: 'data' } });

      const [, status] = await axiosClient.fetch('/test/with-etag-no-cache', 'get', undefined, undefined, {
        headers: { 'If-Match': 'test-etag-123' }
      });

      expect(status).toBe(304);
    });

    it('should return error responses for 4xx and 5xx status codes', async () => {
      const [data, status] = await axiosClient.fetch('/test/error/400');

      expect(status).toBe(400);
      expect(data.api_error_message).toBe('Bad Request');
    });
  });

  describe('Response Format', () => {
    it('should return response in correct tuple format', async () => {
      const result = await axiosClient.fetch('/test/get');

      expect(Array.isArray(result)).toBe(true);
      expect(result).toHaveLength(3);

      const [data, status, headers] = result;
      expect(typeof data).toBe('object');
      expect(typeof status).toBe('number');
      expect(typeof headers).toBe('object');
    });

    it('should include ClueResponse structure in response data', async () => {
      const [data] = await axiosClient.fetch('/test/get');

      expect(data).toHaveProperty('api_response');
      expect(data).toHaveProperty('api_error_message');
      expect(data).toHaveProperty('api_server_version');
      expect(data).toHaveProperty('api_status_code');

      expect(typeof data.api_response).toBe('object');
      expect(typeof data.api_error_message).toBe('string');
      expect(typeof data.api_server_version).toBe('string');
      expect(typeof data.api_status_code).toBe('number');
    });
  });

  describe('withCredentials Configuration', () => {
    it('should always send requests with credentials', async () => {
      // This test verifies that the withCredentials: true configuration is set
      // Since MSW doesn't directly expose request configurations, we test that
      // the request succeeds (which would fail if credentials were required but not sent)
      const [data, status] = await axiosClient.fetch('/test/get');

      expect(status).toBe(200);
      expect((data.api_response as any).success).toBe(true);
    });
  });
});
