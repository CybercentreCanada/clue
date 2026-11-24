import { hget } from 'api';
import { expect, it, vi } from 'vitest';
import { get } from './index';

vi.mock('api', { spy: true });

it('sends the supplied sync limit alongside the checkpoint parameters', async () => {
  vi.mocked(hget).mockResolvedValueOnce([]);

  await get('selectors', 1000, 'last-id', 123, true);

  expect(hget).toHaveBeenCalledWith(
    '/api/v1/sync/selectors',
    new URLSearchParams({ limit: '1000', id: 'last-id', updated_at: '123', omit_deleted: 'true' }),
    undefined
  );
});
