import { renderHook, waitFor } from '@testing-library/react';
import api from 'api';
import { detectType } from 'lib/utils/typeDetection';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import useClueTypeConfig from './useClueTypeConfig';

vi.mock('api', () => ({
  default: {
    lookup: {
      types: { get: vi.fn() },
      types_detection: { get: vi.fn() }
    },
    v2: {
      lookup: {
        types_detection: { get: vi.fn() }
      }
    }
  }
}));

describe('useClueTypeConfig', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.lookup.types.get).mockResolvedValue({ example: ['fallback', 'preferred', 'explicit'] });
    vi.mocked(api.v2.lookup.types_detection.get).mockResolvedValue({
      fallback: { regex: '^.+$', case_sensitive: true },
      preferred: { regex: '^match$', case_sensitive: false, priority: 10 },
      explicit: { regex: null, case_sensitive: false }
    });
  });

  it('loads V2 metadata and preserves the public regex map and supported-type list', async () => {
    const { result } = renderHook(() => useClueTypeConfig(true, '', false));
    await waitFor(() => expect(result.current.typeDetectors).toHaveLength(2));

    expect(api.lookup.types_detection.get).not.toHaveBeenCalled();
    expect(result.current.availableSources).toEqual(['example']);
    expect(result.current.supportedTypes).toEqual(['fallback', 'preferred', 'explicit']);
    expect(Object.keys(result.current.typesDetection)).toEqual(['preferred', 'fallback']);
    expect(result.current.typesDetection.preferred.flags).toBe('i');
    expect(result.current.typesDetection.fallback.flags).toBe('');
    expect(detectType('MATCH', result.current.typeDetectors)).toBe('preferred');
  });

  it('forwards the authentication and network configuration to V2', async () => {
    const onNetworkCall = vi.fn(config => ({ ...config, timeout: 5000 }));
    renderHook(() => useClueTypeConfig(true, 'https://clue.example', false, () => 'token', onNetworkCall));
    await waitFor(() => expect(api.v2.lookup.types_detection.get).toHaveBeenCalledOnce());
    expect(api.v2.lookup.types_detection.get).toHaveBeenCalledWith({
      baseURL: 'https://clue.example',
      headers: { Authorization: 'Bearer token' },
      timeout: 5000
    });
  });

  it('does not fetch until ready', () => {
    renderHook(() => useClueTypeConfig(false, '', false));
    expect(api.lookup.types.get).not.toHaveBeenCalled();
    expect(api.v2.lookup.types_detection.get).not.toHaveBeenCalled();
  });
});
