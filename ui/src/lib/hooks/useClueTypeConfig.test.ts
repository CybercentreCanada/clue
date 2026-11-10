import { renderHook, waitFor } from '@testing-library/react';
import api from 'api';
import { describe, expect, it, vi } from 'vitest';
import useClueTypeConfig from './useClueTypeConfig';

describe('useClueTypeConfig', () => {
  it('fetches V2 metadata with request hooks and compiles ordered detectors', async () => {
    const types = vi.spyOn(api.lookup.types, 'get').mockResolvedValueOnce({ plugin: ['domain', 'ticket'] });
    const metadata = vi.spyOn(api.v2.lookup.types_detection, 'get').mockResolvedValueOnce({
      fallback: { regex: '^.+$', case_sensitive: true, priority: -1 },
      domain: { regex: '^[a-z]+\\.com$', case_sensitive: false },
      ticket: { regex: '^ticket-\\d+$', case_sensitive: true, priority: 5 }
    });
    const onNetworkCall = vi.fn(config => ({ ...config, timeout: 123 }));
    const { result, unmount } = renderHook(() =>
      useClueTypeConfig(true, 'https://clue.example', false, () => 'token', onNetworkCall)
    );
    await waitFor(() => expect(result.current.typeDetectors).toHaveLength(3));
    const expectedConfig = {
      baseURL: 'https://clue.example',
      headers: { Authorization: 'Bearer token' },
      timeout: 123
    };
    expect(types).toHaveBeenCalledWith(expectedConfig);
    expect(metadata).toHaveBeenCalledWith(expectedConfig);
    expect(result.current.typeDetectors.map(([type]) => type)).toEqual(['ticket', 'domain', 'fallback']);
    expect(result.current.typesDetection.domain.test('EXAMPLE.COM')).toBe(true);
    expect(result.current.typesDetection.ticket.test('TICKET-123')).toBe(false);
    expect(result.current.supportedTypes).toEqual(['domain', 'ticket']);
    expect(result.current.availableSources).toEqual(['plugin']);
    unmount();
    vi.restoreAllMocks();
  });
});
