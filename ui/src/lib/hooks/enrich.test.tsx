import { act, renderHook, RenderHookResult, waitFor } from '@testing-library/react';
import { hpost } from 'api';
import buildDatabase from 'lib/database';
import { Selector } from 'lib/types/lookup';
import cloneDeep from 'lodash-es/cloneDeep';
import range from 'lodash-es/range';
import set from 'lodash-es/set';
import sortBy from 'lodash-es/sortBy';
import { v4 as uuid } from 'uuid';
import { describe, it } from 'vitest';
import enrichExample from '../../tests/models/enrich.example.json';
import { MOCK_RESPONSES } from '../../tests/server-handlers';
import { ClueEnrichContextType } from './ClueEnrichContextType';
import { ClueEnrichProps } from './ClueEnrichProps';
import { ClueProvider } from './ClueProvider';
import { useClueEnrichSelector } from './selectors';

// Configuration for testing - chunk size determines how many selectors are processed together
const ENRICH_CHUNK_SIZE = 5;

// Mock the API module to intercept HTTP calls during testing
vi.mock('api', { spy: true });

// Mock functions for the ClueProvider dependencies
const getToken = vi.fn(() => 'example token');
const onNetworkCall = vi.fn(conf => conf);
const pickSources: ClueEnrichProps['pickSources'] = vi.fn(sources => sources);

// Initialize test database
const database = await buildDatabase({ devMode: false, storageType: 'memory' });

// Test wrapper component that provides the enrichment context
const Wrapper = ({ children }) => {
  return (
    <ClueProvider
      ready
      database={database}
      getToken={getToken}
      onNetworkCall={onNetworkCall}
      pickSources={pickSources}
      chunkSize={ENRICH_CHUNK_SIZE}
      debugLogging={!!process.env.ENABLE_DEBUG_LOGGNIG}
      config={MOCK_RESPONSES['/api/v1/configs']}
      skipConfigCall
    >
      {children}
    </ClueProvider>
  );
};

/**
 * Test suite for the enrichment functionality
 * Tests the various aspects of the enrichment system including:
 * - Available sources and types
 * - Type guessing
 * - Single and bulk enrichment
 * - Queue-based enrichment
 * - Error handling and retries
 */
describe('enrich functionality', () => {
  /**
   * Test that the system correctly returns the list of available enrichment sources
   * from the mocked API response
   */
  it('should return the expected list of available sources', async () => {
    const { result } = await act(async () => {
      return renderHook(() => useClueEnrichSelector(ctx => ctx.availableSources), { wrapper: Wrapper });
    });

    expect(result.current).toEqual(['example', 'potato']);
  });

  /**
   * Test that the system correctly returns the available types for enrichment
   * based on the types detection configuration
   */
  it('should return the expected list of available types', async () => {
    const { result } = await act(async () => {
      return renderHook(() => useClueEnrichSelector(ctx => ctx.typesDetection), { wrapper: Wrapper });
    });

    expect(Object.keys(result.current)).toEqual(['ip', 'sha256']);
  });

  /**
   * Tests for the guessType functionality that automatically detects
   * the type of a given value based on regex patterns
   */
  describe('guessType', () => {
    let hook: RenderHookResult<(value: string) => string, any>;
    beforeAll(async () => {
      hook = await act(async () => {
        return renderHook(() => useClueEnrichSelector(ctx => ctx.guessType), { wrapper: Wrapper });
      });
    });

    /**
     * Test that the type guessing works correctly for both valid and invalid inputs
     * Should match IP addresses and SHA256 hashes based on regex patterns
     */
    it('should guess types based on best effort', async () => {
      // valid versions
      expect(hook.result.current('127.0.0.1')).toBe('ip');
      expect(hook.result.current('abcdabcd')).toBe('sha256');

      // invalid versions
      expect(hook.result.current(null)).toBe(null);
      expect(hook.result.current('abc')).toBe(null);
    });

    /**
     * Test that type guessing handles case-insensitive matching
     * Should convert uppercase strings to lowercase before matching
     */
    it('should test lowercased versions of strings', () => {
      expect(hook.result.current('ABCDEF')).toBe('sha256');
    });
  });

  /**
   * Tests for the single enrichment functionality
   * This tests enriching one selector at a time and includes:
   * - Basic enrichment flow
   * - Input validation
   * - Caching behavior
   * - Error handling
   */
  describe('enrich', () => {
    const testData: [string, string] = ['ip', '127.0.0.1'];

    let hook: RenderHookResult<ClueEnrichContextType['enrich'], any>;
    beforeAll(async () => {
      // For whatever reason, database.selectors.remove() hangs.
      await database.selectors.find({ selector: { id: { $exists: true } } }).remove();
      await database.status.find({ selector: { id: { $exists: true } } }).remove();

      hook = await act(async () => {
        return renderHook(() => useClueEnrichSelector(ctx => ctx.enrich), { wrapper: Wrapper });
      });
    });

    beforeEach(() => {
      vi.mocked(hpost).mockClear();
    });

    /**
     * Test the basic enrichment flow for a single selector
     * Should make proper API call and return enriched data
     */
    it('should allow enrichment of a single selector', async () => {
      const result = await hook.result.current(...testData);

      expect(hpost).toBeCalledWith(
        '/api/v1/lookup/enrich?classification=TLP%3ACLEAR&max_timeout=5',
        [{ type: 'ip', value: '127.0.0.1', classification: 'TLP:CLEAR' }],
        expect.objectContaining({ headers: { Authorization: 'Bearer example token' } })
      );

      expect(result.example.latency).toBe(18);
      expect(result).toEqual(enrichExample);
    });

    /**
     * Test that the system handles invalid inputs gracefully
     * Should not make API calls and return empty results for null inputs
     */
    it('should gracefully handle invalid input', async () => {
      const result = await hook.result.current(null, null);

      expect(hpost).not.toBeCalled();

      expect(result).toEqual({});
    });

    /**
     * Test that enrichment results are cached in the database
     * Should be able to retrieve the cached selector data after enrichment
     */
    it('should cache results of selector queries', async () => {
      const matches = await database.selectors
        .find({
          selector: {
            value: testData[1]
          }
        })
        .exec();

      expect(
        sortBy(
          matches.map(_match => [_match.value, _match.source]),
          '0'
        )
      ).toEqual([
        ['127.0.0.1', 'example'],
        ['127.0.0.1', 'example']
      ]);
    });

    /**
     * Test that old cache results are replaced with new ones
     * Should update latency values and maintain only the latest results
     */
    it('should purge old cache results', async () => {
      enrichExample.example.latency = 20;
      vi.mocked(hpost).mockImplementationOnce(() =>
        Promise.resolve({
          ip: {
            '127.0.0.1': cloneDeep(enrichExample)
          }
        })
      );

      const result = await hook.result.current(...testData);

      expect(hpost).toBeCalledWith(
        '/api/v1/lookup/enrich?classification=TLP%3ACLEAR&max_timeout=5',
        [{ type: 'ip', value: '127.0.0.1', classification: 'TLP:CLEAR' }],
        expect.objectContaining({ headers: { Authorization: 'Bearer example token' } })
      );

      expect(result.example.latency).toBe(20);

      enrichExample.example.latency = 18;

      await hook.result.current(...testData);

      const matches = await database.selectors
        .find({
          selector: {
            value: testData[1]
          }
        })
        .exec();

      expect(matches.length).toBe(2);

      expect(
        sortBy(
          matches.map(_match => [_match.value, _match.latency]),
          '0'
        )
      ).toEqual([
        ['127.0.0.1', 18],
        ['127.0.0.1', 18]
      ]);
    });

    /**
     * Test that network errors during enrichment are handled gracefully
     * Should return empty results when the API call fails
     */
    it('should handle network-based enrichment errors gracefully', async () => {
      vi.mocked(hpost).mockRejectedValueOnce('example error');

      const result = await hook.result.current(...testData);

      expect(result).toEqual({});
    });

    /**
     * Test that server-side errors in enrichment responses are handled properly
     * Should preserve error information in the returned results
     */
    it('should handle server-based enrichment errors gracefully', async () => {
      const modifiedResult = cloneDeep(enrichExample);

      modifiedResult.example.items = [];
      modifiedResult.example.error = 'example error';

      vi.mocked(hpost).mockImplementationOnce(() =>
        Promise.resolve({
          ip: {
            '127.0.0.1': set(cloneDeep(modifiedResult), 'example.value', '127.0.0.1')
          }
        })
      );

      const result = await hook.result.current(...testData);

      expect(result.example.error).toBe('example error');
    });
  });

  /**
   * Tests for bulk enrichment functionality
   * This tests enriching multiple selectors simultaneously and includes:
   * - Processing multiple selectors in a single request
   * - Caching behavior for bulk operations
   * - Error handling for bulk operations
   */
  describe('bulkEnrich', () => {
    const testData: Selector[] = [
      { type: 'ip', value: '127.0.0.1', classification: 'TLP:CLEAR' },
      { type: 'ip', value: '127.0.0.2', classification: 'TLP:CLEAR' }
    ];

    let hook: RenderHookResult<ClueEnrichContextType['bulkEnrich'], any>;
    beforeAll(async () => {
      // For whatever reason, database.selectors.remove() hangs.
      await database.selectors.find({ selector: { id: { $exists: true } } }).remove();
      await database.status.find({ selector: { id: { $exists: true } } }).remove();

      hook = await act(async () => {
        return renderHook(() => useClueEnrichSelector(ctx => ctx.bulkEnrich), { wrapper: Wrapper });
      });
    });

    beforeEach(() => {
      vi.mocked(hpost).mockClear();
    });

    /**
     * Test the bulk enrichment flow for multiple selectors
     * Should make single API call with all selectors and return organized results
     */
    it('should allow enrichment of several selectors simultaneously', async () => {
      const result = await hook.result.current(testData);

      expect(hpost).toBeCalledWith(
        '/api/v1/lookup/enrich?classification=TLP%3ACLEAR&max_timeout=5',
        testData,
        expect.objectContaining({ headers: { Authorization: 'Bearer example token' } })
      );

      expect(result.ip['127.0.0.1'].example.latency).toBe(18);
      expect(result.ip['127.0.0.2'].example.latency).toBe(18);
      expect(result.ip['127.0.0.1']).toEqual(enrichExample);
      expect(result.ip['127.0.0.2']).toEqual(set(enrichExample, 'example.value', '127.0.0.2'));
    });

    /**
     * Test that bulk enrichment results are properly cached
     * Should store all enriched selectors in the database for future use
     */
    it('should cache results of selectors', async () => {
      const matches = await database.selectors
        .find({
          selector: {
            value: {
              $in: testData.map(_entry => _entry.value)
            }
          }
        })
        .exec();

      expect(
        sortBy(
          matches.map(_match => [_match.value, _match.source]),
          '0'
        )
      ).toEqual([
        ['127.0.0.1', 'example'],
        ['127.0.0.1', 'example'],
        ['127.0.0.2', 'example'],
        ['127.0.0.2', 'example']
      ]);
    });

    /**
     * Test that old cached results are replaced when bulk enrichment runs again
     * Should update latency values and maintain data consistency
     */
    it('should purge old cache results', async () => {
      enrichExample.example.latency = 20;
      vi.mocked(hpost).mockImplementationOnce(() =>
        Promise.resolve({
          ip: {
            '127.0.0.1': set(cloneDeep(enrichExample), 'example.value', '127.0.0.1'),
            '127.0.0.2': set(cloneDeep(enrichExample), 'example.value', '127.0.0.2')
          }
        })
      );

      const result = await hook.result.current(testData);

      expect(hpost).toBeCalledWith(
        '/api/v1/lookup/enrich?classification=TLP%3ACLEAR&max_timeout=5',
        testData,
        expect.objectContaining({ headers: { Authorization: 'Bearer example token' } })
      );

      expect(result.ip['127.0.0.1'].example.latency).toBe(20);
      expect(result.ip['127.0.0.2'].example.latency).toBe(20);

      enrichExample.example.latency = 18;

      await hook.result.current(testData);

      const matches = await database.selectors
        .find({
          selector: {
            value: {
              $in: testData.map(_entry => _entry.value)
            }
          }
        })
        .exec();

      expect(matches.length).toBe(4);

      expect(
        sortBy(
          matches.map(_match => [_match.value, _match.latency]),
          '0'
        )
      ).toEqual([
        ['127.0.0.1', 18],
        ['127.0.0.1', 18],
        ['127.0.0.2', 18],
        ['127.0.0.2', 18]
      ]);
    });

    /**
     * Test that network errors during bulk enrichment are handled gracefully
     * Should return empty results when the API call fails
     */
    it('should handle network-based enrichment errors gracefully', async () => {
      vi.mocked(hpost).mockRejectedValueOnce('example error');

      const result = await hook.result.current(testData);

      expect(result).toEqual({});
    });

    /**
     * Test that server-side errors in bulk enrichment responses are handled properly
     * Should preserve error information for all affected selectors
     */
    it('should handle server-based enrichment errors gracefully', async () => {
      const modifiedResult = cloneDeep(enrichExample);

      modifiedResult.example.items = [];
      modifiedResult.example.error = 'example error';

      vi.mocked(hpost).mockImplementationOnce(() =>
        Promise.resolve({
          ip: {
            '127.0.0.1': set(cloneDeep(modifiedResult), 'example.value', '127.0.0.1'),
            '127.0.0.2': set(cloneDeep(modifiedResult), 'example.value', '127.0.0.2')
          }
        })
      );

      const result = await hook.result.current(testData);

      expect(result.ip['127.0.0.1'].example.error).toBe('example error');
      expect(result.ip['127.0.0.2'].example.error).toBe('example error');
    });
  });

  /**
   * Tests for queue-based enrichment functionality
   * This tests the asynchronous queue system that batches enrichment requests:
   * - Input validation
   * - Queue accumulation and processing
   * - Chunking large requests
   * - Status tracking with observables
   */
  describe('queueEnrich', () => {
    let hook: RenderHookResult<ClueEnrichContextType['queueEnrich'], any>;
    beforeEach(async () => {
      vi.mocked(hpost).mockClear();

      // For whatever reason, database.selectors.remove() hangs.
      await database.status.find({ selector: { id: { $exists: true } } }).remove();
      await database.selectors.find({ selector: { id: { $exists: true } } }).remove();

      hook = await act(async () => {
        return renderHook(() => useClueEnrichSelector(ctx => ctx.queueEnrich), { wrapper: Wrapper });
      });
    });

    /**
     * Test that the queue system properly validates input parameters
     * Should throw appropriate errors for null type or value
     */
    it('should raise errors on invalid input', async () => {
      await expect(() => hook.result.current(null, null)).rejects.toThrow(new Error('Type cannot be null'));

      await expect(() => hook.result.current('ip', null)).rejects.toThrow(new Error('Value cannot be null'));
    });

    /**
     * Test the queue accumulation and processing functionality
     * Should collect multiple selectors and process them together in a batch
     * Tests the observable status tracking system
     */
    it('should allow users to queue selectors for enrichment', async () => {
      hook.result.current('ip', '127.0.0.1');
      const result = await hook.result.current('ip', '127.0.0.2');

      let status = result.status;
      result.status$.subscribe(value => (status = value));

      await waitFor(() => expect(status).toBe('complete'));

      expect(hpost).toHaveBeenCalledOnce();
      expect(hpost).toBeCalledWith(
        '/api/v1/lookup/enrich?classification=TLP%3ACLEAR&max_timeout=5',
        expect.arrayContaining([
          { type: 'ip', value: '127.0.0.1', classification: 'TLP:CLEAR' },
          { type: 'ip', value: '127.0.0.2', classification: 'TLP:CLEAR' }
        ]),
        expect.objectContaining({ headers: { Authorization: 'Bearer example token' } })
      );

      const matches = await database.selectors
        .find({
          selector: {
            value: {
              $in: ['127.0.0.1', '127.0.0.2']
            }
          }
        })
        .exec();

      expect(matches.length).toBe(4);
    });

    it('should chunk large numbers of selectors for enrichment', async () => {
      const CHUNK_SIZE = 35;
      const mockData: Selector[] = range(1, CHUNK_SIZE + 1).map(_number => ({
        type: 'ip',
        value: `127.0.0.${_number}`
      }));

      await act(async () => {
        await Promise.all(mockData.map(entry => hook.result.current(entry.type, entry.value)));

        await waitFor(
          async () =>
            expect(
              await database.status.count({ selector: { status: { $in: ['pending', 'in-progress'] } } }).exec()
            ).toBe(0),
          { timeout: 2000 }
        );
      });

      const matches = await database.selectors
        .find({
          selector: {
            value: {
              $in: mockData.map(entry => entry.value)
            }
          }
        })
        .exec();

      // 100 chunked into chunks of 15 -> 7 chunks required
      expect(hpost).toBeCalledTimes(Math.ceil(CHUNK_SIZE / ENRICH_CHUNK_SIZE));

      // All values should have a result now
      expect(matches.length).toBe(CHUNK_SIZE * 2);
    });
  });

  describe('enrichFailedEnrichments', () => {
    let hook: RenderHookResult<ClueEnrichContextType['enrichFailedEnrichments'], any>;
    beforeAll(async () => {
      hook = await act(async () => {
        return renderHook(() => useClueEnrichSelector(ctx => ctx.enrichFailedEnrichments), { wrapper: Wrapper });
      });
    });

    beforeEach(async () => {
      vi.mocked(hpost).mockClear();

      // For whatever reason, database.selectors.remove() hangs.
      await database.status.find({ selector: { id: { $exists: true } } }).remove();
      await database.selectors.find({ selector: { id: { $exists: true } } }).remove();
    });

    it('should do nothing if there are no errors', async () => {
      await database.selectors.insert({
        id: uuid(),
        source: 'example',
        type: 'ip',
        value: '127.0.0.1',
        annotations: [],
        classification: 'TLP:CLEAR',
        latency: 20,
        count: 1
      });

      await hook.result.current();

      expect(hpost).not.toBeCalled();
    });

    it('should re-enrich failed enrichments', async () => {
      await database.selectors.insert({
        id: uuid(),
        source: 'example',
        type: 'ip',
        value: '127.0.0.1',
        annotations: [],
        classification: 'TLP:CLEAR',
        latency: 20,
        count: 1,
        error: 'example error'
      });

      await hook.result.current();

      const statuses = await database.status.find({ selector: { value: '127.0.0.1' } }).exec();

      expect(statuses.length).toBe(1);

      let status = statuses[0].status;
      statuses[0].status$.subscribe(value => (status = value));

      await waitFor(() => expect(status).toBe('complete'));

      expect(hpost).toHaveBeenCalledOnce();
      expect(hpost).toBeCalledWith(
        '/api/v1/lookup/enrich?sources=example&classification=TLP%3ACLEAR&max_timeout=5',
        [{ type: 'ip', value: '127.0.0.1', classification: 'TLP:CLEAR' }],
        expect.objectContaining({ headers: { Authorization: 'Bearer example token' } })
      );
    });
  });
});
