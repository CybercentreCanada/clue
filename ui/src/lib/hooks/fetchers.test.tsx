import { act, renderHook, RenderHookResult } from '@testing-library/react';
import { hpost } from 'api';
import buildDatabase from 'lib/database';
import type { FetcherResult } from 'lib/types/fetcher';
import type { Selector } from 'lib/types/lookup';
import { describe, it } from 'vitest';
import exampleFetcher from '../../tests/models/fetcher.example.json';
import { ClueProvider } from './ClueProvider';
import { useClueFetcherSelector } from './selectors';

vi.mock('api', { spy: true });

const getToken = vi.fn(() => 'example token');
const onNetworkCall = vi.fn(conf => conf);

const database = await buildDatabase({ devMode: false, storageType: 'memory' });

const Wrapper = ({ children }) => {
  return (
    <ClueProvider
      ready
      database={database}
      getToken={getToken}
      onNetworkCall={onNetworkCall}
      debugLogging={!!process.env.ENABLE_DEBUG_LOGGNIG}
    >
      {children}
    </ClueProvider>
  );
};

describe('fetcher functionality', () => {
  it('should call useContextSelector with correct context and selector', async () => {
    const { result } = await act(async () => {
      return renderHook(
        () => useClueFetcherSelector(ctx => ({ fetchers: ctx.fetchers, fetchCompleted: ctx.fetchCompleted })),
        { wrapper: Wrapper }
      );
    });

    expect(result.current.fetchers['example.fetcher']).toEqual(exampleFetcher);
    expect(result.current.fetchCompleted).toBe(true);
  });

  describe('fetchSelector', () => {
    let hook: RenderHookResult<(fetcherId: string, selector: Selector) => Promise<FetcherResult>, any>;
    beforeAll(async () => {
      hook = await act(async () => {
        return renderHook(() => useClueFetcherSelector(ctx => ctx.fetchSelector), { wrapper: Wrapper });
      });
    });

    beforeEach(() => {
      vi.mocked(hpost).mockClear();
    });

    it('should allow fetching renderings of selectors', async () => {
      const fetchResult = await hook.result.current('example.fetcher', { type: 'ip', value: 'example' });

      expect(vi.mocked(hpost)).toBeCalledWith(
        '/api/v1/fetchers/example/fetcher',
        { type: 'ip', value: 'example' },
        expect.objectContaining({ headers: { Authorization: 'Bearer example token' } })
      );

      expect(fetchResult.outcome).toBe('success');
      expect(fetchResult.data.hello).toBe('world');
    });

    it('should reuse existing calls', async () => {
      const fetchResult = await hook.result.current('example.fetcher', { type: 'ip', value: 'example' });

      expect(vi.mocked(hpost)).not.toBeCalled();

      expect(fetchResult.outcome).toBe('success');
      expect(fetchResult.data.hello).toBe('world');
    });
  });
});
