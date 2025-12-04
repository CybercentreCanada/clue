/* eslint-disable no-console */
import { addAPIProvider } from '@iconify/react';
import api from 'api';
import * as lookup from 'api/lookup';
import type { AxiosRequestConfig } from 'axios';
import type { SelectorDocType, StatusDocType } from 'lib/database/types';
import type { EnrichResponse, EnrichResponses, Selector } from 'lib/types/lookup';
import { clueDebugLogger } from 'lib/utils/loggerUtil';
import chunk from 'lodash-es/chunk';
import debounce from 'lodash-es/debounce';
import groupBy from 'lodash-es/groupBy';
import uniq from 'lodash-es/uniq';
import uniqBy from 'lodash-es/uniqBy';
import type { FC, PropsWithChildren } from 'react';
import { useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { createContext } from 'use-context-selector';
import { v4 as uuid } from 'uuid';
import { ClueDatabaseContext } from './ClueDatabaseContext';
import type { ClueEnrichContextType } from './ClueEnrichContextType';
import type { ClueEnrichProps } from './ClueEnrichProps';
import useClueConfig from './useClueConfig';
import useClueTypeConfig from './useClueTypeConfig';

export const ClueEnrichContext = createContext<ClueEnrichContextType>(null);

export const ClueEnrichProvider: FC<PropsWithChildren<ClueEnrichProps>> = ({
  children,
  classification: _defaultClassification,
  baseURL,
  getToken,
  onNetworkCall,
  pickSources,
  chunkSize = 15,
  maxRequestCount = 4,
  defaultTimeout = 5,
  enabled = true,
  ready = false,
  publicIconify = true,
  skipConfigCall = false,
  customIconify: _customIconify,
  debugLogging = true
}) => {
  const clueConfig = useClueConfig();
  const database = useContext(ClueDatabaseContext);


  const [configuredDefaultClassification, setConfiguredDefaultClassification] = useState<string>(null);
  const defaultClassification = useMemo(
    () => configuredDefaultClassification ?? _defaultClassification ?? clueConfig.config?.c12nDef?.RESTRICTED,
    [_defaultClassification, clueConfig.config?.c12nDef?.RESTRICTED, configuredDefaultClassification]
  );

  const setDefaultClassification: ClueEnrichContextType['setDefaultClassification'] = useCallback(
    func => setConfiguredDefaultClassification(func(clueConfig.config?.c12nDef)),
    [clueConfig.config?.c12nDef]
  );

  /**
   * Is the Clue Provider ready to perform queries?
   */
  const [isReady, setIsReady] = useState<boolean>(ready);

  /**
   * Count of the currently running network requests.
   */
  const runningRequestCount = useRef(0);

  /**
   * The sources the user wants to use for the requests
   */
  const [sources, setSources] = useState<string[]>([]);

  // Initialize the sources and type detection for the user
  const { availableSources, typesDetection } = useClueTypeConfig(
    enabled && isReady,
    baseURL,
    debugLogging,
    getToken,
    onNetworkCall
  );

  useEffect(() => {
    if (skipConfigCall || !enabled || !isReady) {
      return;
    }

    const headers: AxiosRequestConfig['headers'] = {};
    const token = getToken?.();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    let requestConfig: AxiosRequestConfig = { baseURL, headers };
    if (onNetworkCall) {
      requestConfig = onNetworkCall(requestConfig);
    }

    api.configs.get(requestConfig).then(clueConfig.setConfig);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseURL, onNetworkCall, skipConfigCall, isReady]);

  const [customIconify, setCustomIconify] = useState(_customIconify);
  useEffect(() => {
    if (_customIconify) {
      setCustomIconify(_customIconify);
    }
  }, [_customIconify]);

  useEffect(() => {
    if (publicIconify) {
      return;
    }

    let iconURL = customIconify ?? import.meta.env.VITE_ICONIFY_TARGET ?? baseURL?.replace(/^[^.]+/, 'icons');
    // Ensuring window exists (may be missing in some test environments, in some circumstances)
    if (!iconURL && typeof window !== 'undefined' && !!window && !window.location.origin.includes('localhost')) {
      iconURL = window.location.protocol + '//' + window.location.origin.replace(/^[^.]+/, 'icons');
    }

    if (iconURL) {
      clueDebugLogger(`Using ${iconURL} for iconify`, debugLogging);
      addAPIProvider('', {
        resources: [iconURL]
      });
    }
  }, [baseURL, customIconify, debugLogging, publicIconify]);

  const _addEntries = useCallback(
    async (entries: EnrichResponse[]) => {
      const newRecords: SelectorDocType[] = [];

      for (const entry of entries) {
        const { latency, source, type, value, items, error } = entry;

        if (error) {
          newRecords.push({
            id: uuid(),
            source,
            type,
            value,
            annotations: [],
            classification: defaultClassification,
            latency,
            count: 0,
            error
          });
        }

        for (const item of items) {
          const { classification, count, link, annotations } = item;

          await database.selectors.find({ selector: { type, value, source, classification } }).incrementalRemove();

          const record = {
            id: uuid(),
            source,
            type,
            value,
            annotations,
            classification,
            latency,
            count,
            link,
            error
          };

          if (newRecords.some(_entry => _entry.id === record.id)) {
            record.id = uuid();
          }

          newRecords.push(record);
        }
      }

      const result = await database.selectors.bulkInsert(newRecords);

      if (result.error.length > 0) {
        console.warn('Errors on upsert:');

        result.error.forEach(err => console.warn(err.documentId, (err as any).validationErrors ?? err.status));
      }
    },
    [database, defaultClassification]
  );

  const enrich: ClueEnrichContextType['enrich'] = useCallback(
    async (type, value, _options = {}) => {
      if (!type || !value) {
        console.error(`Type (${type}) or value (${value}) is empty, returning empty response`);
        return {};
      }

      const _sources =
        pickSources?.(sources, availableSources, [{ type, value, classification: _options.classification }]) ?? sources;

      const options = {
        timeout: defaultTimeout,
        force: false,
        includeRaw: false,
        noCache: false,
        classification: defaultClassification,
        sources: _sources,
        ..._options
      };

      const headers: AxiosRequestConfig['headers'] = {};
      const token = getToken?.();
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }

      let requestConfig: AxiosRequestConfig = { baseURL, headers };
      if (onNetworkCall) {
        requestConfig = onNetworkCall(requestConfig);
      }

      const selector: Selector = {
        type,
        value,
        classification: options.classification
      };

      let statusRecord = await database.status?.findOne({ selector: { ...selector } }).exec();

      if (!statusRecord) {
        statusRecord = await database.status?.insert({
          id: uuid(),
          type: selector.type,
          value: selector.value,
          classification: selector.classification ?? defaultClassification,
          status: 'in-progress'
        });
      } else {
        await statusRecord.incrementalPatch({ status: 'in-progress' });
      }

      try {
        const enrichmentResult = await lookup.enrich.post([selector], options.sources, options, requestConfig);

        const enrichData: EnrichResponses = Object.values(Object.values(enrichmentResult)[0])[0];

        await statusRecord?.incrementalPatch({ status: 'complete' });

        await _addEntries(Object.values(enrichData));

        return enrichData;
      } catch (e) {
        console.error(e);
        return {};
      }
    },
    [
      _addEntries,
      availableSources,
      baseURL,
      database,
      defaultClassification,
      defaultTimeout,
      getToken,
      onNetworkCall,
      pickSources,
      sources
    ]
  );

  const bulkEnrich: ClueEnrichContextType['bulkEnrich'] = useCallback(
    async (bulkRequest, _options) => {
      const _sources = pickSources?.(sources, availableSources, bulkRequest) ?? sources;

      const options = {
        timeout: defaultTimeout,
        includeRaw: false,
        noCache: false,
        classification: defaultClassification,
        sources: _sources,
        ..._options
      };

      const headers: AxiosRequestConfig['headers'] = {};
      const token = getToken?.();
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }

      let requestConfig: AxiosRequestConfig = { baseURL, headers };
      if (onNetworkCall) {
        requestConfig = onNetworkCall(requestConfig);
      }

      const statuses: StatusDocType[] = [];
      for (const selector of bulkRequest) {
        const query = { type: selector.type, value: selector.value, classification: options.classification };
        let statusRecord = await database.status
          .findOne({
            selector: query
          })
          .incrementalPatch({
            status: 'in-progress'
          });

        if (!statusRecord) {
          statusRecord = await database.status.insert({
            id: uuid(),
            ...query,
            status: 'in-progress',
            sources: options.sources
          });
        }

        statuses.push(statusRecord.toMutableJSON());
      }

      try {
        const result = await lookup.enrich.post(bulkRequest, options.sources, options, requestConfig);

        // Drilling down - type -> value -> plugin. The result is the query
        const entries = Object.values(result)
          .flatMap<EnrichResponses>(Object.values)
          .flatMap<EnrichResponse>(Object.values);

        await _addEntries(entries);

        return result;
      } catch (e) {
        console.error(e);
        return {};
      } finally {
        database.status.bulkUpsert(
          uniqBy(statuses, _record => _record.id).map(record => {
            record.status = 'complete';

            return record;
          })
        );
      }
    },
    [
      pickSources,
      sources,
      availableSources,
      defaultTimeout,
      defaultClassification,
      getToken,
      baseURL,
      onNetworkCall,
      database,
      _addEntries
    ]
  );

  const enrichFailedEnrichments = useCallback(async () => {
    const failedEnrichments = await database.selectors.find({ selector: { error: { $exists: true } } }).exec();

    const byClassification = groupBy(failedEnrichments, 'classification');

    const newRequests: StatusDocType[] = [];
    for (const [classification, selectors] of Object.entries(byClassification)) {
      const bySelector = groupBy(selectors, _selector => `${_selector.type}:${_selector.value}`);

      Object.values(bySelector).forEach(records => {
        newRequests.push({
          id: uuid(),
          type: records[0].type,
          value: records[0].value,
          classification,
          sources: uniq(records.map(_record => _record.source)).sort(),
          status: 'pending'
        });
      });
    }

    await database.status.bulkInsert(newRequests);

    await database.selectors.bulkRemove(failedEnrichments);
  }, [database]);

  const enrichQueued: () => void = useMemo(
    () =>
      debounce(
        async () => {
          if (!database?.status) {
            return;
          } else if (database.status.closed) {
            console.warn('Status database is closed, will not enrich');
            return;
          }

          // Get a list of requests to send
          const selectors = await database.status
            .find({ selector: { status: 'pending' } })
            .update({ $set: { status: 'in-progress' } });

          if (selectors.length < 1) {
            return;
          }

          const chunks = chunk(selectors, chunkSize);

          clueDebugLogger(
            `Enriching ${selectors.length} selectors in ${chunks.length} chunks of ${chunkSize}.`,
            debugLogging
          );

          await Promise.all(
            // For performance reasons, we chunk the requests. This will allow us to take advantage of parellelization in the
            // backend, both on the pod level and kubernetes level
            chunks.map(async reqsChunk => {
              let _interval = null;
              if (runningRequestCount.current <= maxRequestCount) {
                runningRequestCount.current += 1;
              } else {
                let startOfWait = Date.now();
                await new Promise<void>(res => {
                  _interval = setInterval(() => {
                    clueDebugLogger(
                      `Waiting on ${runningRequestCount.current} existing requests to complete (total delay: ${
                        Date.now() - startOfWait
                      }ms)`,
                      debugLogging
                    );

                    if (runningRequestCount.current < maxRequestCount) {
                      res();
                    }
                  }, 400);
                }).finally(() => {
                  runningRequestCount.current += 1;
                  clearInterval(_interval);
                });
              }

              try {
                const options: { [index: string]: any } = {};

                const _sources = uniq(reqsChunk.flatMap(record => record.sources ?? []));
                if (_sources.length > 0) {
                  options.sources = _sources;
                }

                await bulkEnrich(
                  reqsChunk.map(record => record.toSelector()),
                  options
                );

                await database.status
                  .findByIds(reqsChunk.map(selector => selector.id))
                  .update({ $set: { status: 'complete' } });
              } catch (e) {
                console.error(e);
              } finally {
                runningRequestCount.current -= 1;
                if (_interval) {
                  clearInterval(_interval);
                }
              }
            })
          );
        },
        200,
        { maxWait: 500, leading: false }
      ),
    [bulkEnrich, chunkSize, database, debugLogging, maxRequestCount]
  );

  useEffect(() => {
    if (!database || import.meta.env.PROD) {
      return;
    }

    const observer = database.status
      .count({ selector: { $or: [{ status: 'pending' }, { status: 'in-progress' }] } })
      .$.subscribe(count => clueDebugLogger(`Outstanding requests: ${count}`, debugLogging));

    return () => {
      try {
        observer.unsubscribe();
      } catch {}
    };
  }, [database, debugLogging]);

  useEffect(() => {
    if (!enabled || !isReady || !database?.status) {
      return;
    }

    const observer = database.status
      .find({
        selector: {
          status: 'pending'
        }
      })
      .$.subscribe(() => enrichQueued());

    return () => {
      try {
        observer?.unsubscribe();
      } catch (e) {
        console.warn(e);
      }
    };
  }, [enabled, isReady, database, debugLogging, enrichQueued]);

  const queueEnrich: ClueEnrichContextType['queueEnrich'] = useCallback(
    async (type, value, classification) => {
      if (!type) {
        throw new Error('Type cannot be null');
      }

      if (!value) {
        throw new Error('Value cannot be null');
      }

      const query = { type, value, classification: classification ?? defaultClassification };

      let statusRecord = await database.status
        .findOne({
          selector: query
        })
        .exec();

      if (!statusRecord) {
        statusRecord = await database.status.queueInsert({
          id: uuid(),
          ...query,
          status: 'pending'
        });
      }

      return statusRecord;
    },
    [defaultClassification, database]
  );

  const guessType: ClueEnrichContextType['guessType'] = useCallback(
    value => {
      if (!value) {
        return null;
      }

      const types = Object.entries(typesDetection);

      const regularCheck = types.find(([_type, _regexp]) => _regexp.exec(value))?.[0];
      if (regularCheck) {
        return regularCheck;
      }

      const lowercased = value.toLowerCase();
      const lowercaseCheck = types.find(([_type, _regexp]) => _regexp.exec(lowercased))?.[0];
      if (lowercaseCheck) {
        return lowercaseCheck;
      }

      return null;
    },
    [typesDetection]
  );

  const value: ClueEnrichContextType = useMemo(
    () => ({
      bulkEnrich,
      enrich,
      enrichFailedEnrichments,
      sources,
      setSources,
      typesDetection,
      availableSources,
      guessType,
      queueEnrich,
      setCustomIconify,
      setDefaultClassification,
      setReady: setIsReady,
      defaultClassification,
      ready: isReady && !!database && !!clueConfig.config?.c12nDef
    }),
    [
      bulkEnrich,
      enrich,
      enrichFailedEnrichments,
      sources,
      typesDetection,
      availableSources,
      guessType,
      queueEnrich,
      setDefaultClassification,
      defaultClassification,
      isReady,
      database,
      clueConfig.config?.c12nDef
    ]
  );

  return <ClueEnrichContext.Provider value={value}>{children}</ClueEnrichContext.Provider>;
};
