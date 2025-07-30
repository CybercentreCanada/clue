// Import necessary types and test utilities
import type { AxiosRequestConfig } from 'axios';
import { describe, expect, it, Mock, vi } from 'vitest';
import { DocumentationResponse, get, uri } from './documentation';

// Mock the api module functions for isolation
vi.mock('api', { spy: true });

// Import mocked functions for type checking
// eslint-disable-next-line import/first
import { hget, joinAllUri, joinUri } from 'api';

const mockedHget = hget as Mock;
const mockedJoinAllUri = joinAllUri as Mock;
const mockedJoinUri = joinUri as Mock;

// Test suite for the Documentation API
// Covers uri, get, and post functions

describe('Documentation API', () => {
  const mockResponse: DocumentationResponse = {
    markdown: 'Hello World'
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Setup default mock implementations for joinUri
    mockedJoinAllUri.mockImplementation((...parts) => parts.filter(Boolean).join('/'));
  });

  // Test the uri() function
  describe('uri', () => {
    it('should construct the correct URI for documentation endpoint', () => {
      const result = uri('example');

      expect(mockedJoinUri).toHaveBeenCalledWith('/api/v1', 'static');
      expect(mockedJoinAllUri).toHaveBeenCalledWith('/api/v1/static', 'docs', 'example');
      expect(result).toBe('/api/v1/static/docs/example');
    });
  });

  // Test the get() function
  describe('get', () => {
    it('should call hget with correct parameters when no config provided', async () => {
      const result = await get('example');

      expect(mockedHget).toHaveBeenCalledWith('/api/v1/static/docs/example', null, undefined);
      expect(result).toEqual(mockResponse);
    });

    it('should call hget with provided config', async () => {
      const config: AxiosRequestConfig = { timeout: 5000 };

      const result = await get('example', config);

      expect(mockedHget).toHaveBeenCalledWith('/api/v1/static/docs/example', null, config);
      expect(result).toEqual(mockResponse);
    });

    it('should handle hget errors', async () => {
      const error = new Error('Network error');
      mockedHget.mockRejectedValue(error);

      await expect(get('example')).rejects.toThrow('Network error');
    });
  });
});
