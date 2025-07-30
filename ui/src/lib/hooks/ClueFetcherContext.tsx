import api from 'api';
import type { AxiosRequestConfig } from 'axios';
import type { FetcherDefinition, FetcherResult } from 'lib/types/fetcher';
import type { Selector } from 'lib/types/lookup';
import type { FC, PropsWithChildren } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createContext } from 'use-context-selector';
import useClue from './useClue';
import useClueConfig from './useClueConfig';

export interface ClueFetcherContextProps {
  /**
   * The base URL that refers to the clue API. leaving this empty will forward requests to the current origin.
   */
  baseURL?: string;

  /**
   * What should the default classification be for indicators?
   */
  classification?: string;

  /**
   * Get an access token for the clue API.
   *
   * @returns An access token valid for use with the clue API.
   */
  getToken?: () => string;

  /**
   * Add modify the Axios request configuration before the request is sent
   * @param config The existing axios request config
   */
  onNetworkCall?: (config: AxiosRequestConfig) => AxiosRequestConfig;
}

export type ClueFetcherContextType = {
  fetchSelector: (fetcherId: string, selector: Selector) => Promise<FetcherResult>;
  fetchers: { [index: string]: FetcherDefinition };
  fetchCompleted: boolean;
};

export const ClueFetcherContext = createContext<ClueFetcherContextType>(null);

export const ClueFetcherProvider: FC<PropsWithChildren<ClueFetcherContextProps>> = ({
  baseURL,
  children,
  classification: _defaultClassification,
  getToken,
  onNetworkCall
}) => {
  const clueConfig = useClueConfig();
  const { ready } = useClue();

  const [defaultClassification, setDefaultClasification] = useState(_defaultClassification);
  const [fetchCompleted, setFetchCompleted] = useState(false);
  const [fetchers, setFetchers] = useState<ClueFetcherContextType['fetchers']>({});

  const fetchRequests = useRef<{ [fetcherId: string]: { [hashKey: string]: Promise<FetcherResult> } }>({});

  /**
   * Return a JSON string containing the type, value and classification of the request being made.
   */
  const getHashKey = useCallback(
    ({ type, value, classification }: Selector) =>
      JSON.stringify({ type, value, classification: classification ?? defaultClassification }),
    [defaultClassification]
  );

  const fetchSelector: ClueFetcherContextType['fetchSelector'] = useCallback(
    async (fetcherId, selector) => {
      if (fetchRequests.current[fetcherId]?.[getHashKey(selector)]) {
        return fetchRequests.current[fetcherId][getHashKey(selector)];
      }

      try {
        const headers: AxiosRequestConfig['headers'] = {};
        const token = getToken?.();
        if (token) {
          headers.Authorization = `Bearer ${token}`;
        }

        let requestConfig: AxiosRequestConfig = { baseURL, headers };
        if (onNetworkCall) {
          requestConfig = onNetworkCall(requestConfig);
        }
        const result = api.fetchers.post(fetcherId, selector, requestConfig);

        if (!fetchRequests.current[fetcherId]) {
          fetchRequests.current[fetcherId] = {};
        }

        fetchRequests.current[fetcherId][getHashKey(selector)] = result;

        return await result;
      } catch {
        return null;
      }
    },
    [baseURL, getHashKey, getToken, onNetworkCall]
  );

  useEffect(() => {
    if (!defaultClassification && clueConfig.config?.c12nDef?.UNRESTRICTED) {
      setDefaultClasification(clueConfig.config?.c12nDef?.UNRESTRICTED);
    }
  }, [clueConfig.config?.c12nDef?.UNRESTRICTED, defaultClassification]);

  useEffect(() => {
    if (!ready) {
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

    api.fetchers
      .get(requestConfig)
      .then(setFetchers)
      .finally(() => setFetchCompleted(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseURL, ready]);

  const context = useMemo(
    () => ({
      fetchSelector,
      fetchers,
      fetchCompleted
    }),
    [fetchCompleted, fetchSelector, fetchers]
  );

  return <ClueFetcherContext.Provider value={context}>{children}</ClueFetcherContext.Provider>;
};
