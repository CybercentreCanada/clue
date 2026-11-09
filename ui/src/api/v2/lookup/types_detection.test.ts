import { hget } from 'api';
import { describe, expect, it, vi } from 'vitest';
import { MOCK_RESPONSES } from '../../../tests/server-handlers';
import { get, uri } from './types_detection';

vi.mock('api', { spy: true });

describe('V2 type detection API', () => {
  it('constructs the V2 path without a V1 prefix', () => {
    expect(uri()).toBe('/api/v2/lookup/types_detection');
  });

  it('gets metadata with the provided request configuration', async () => {
    const config = { timeout: 5000 };
    expect(await get(config)).toEqual(MOCK_RESPONSES['/api/v2/lookup/types_detection']);
    expect(vi.mocked(hget)).toHaveBeenCalledWith('/api/v2/lookup/types_detection', null, config);
  });
});
