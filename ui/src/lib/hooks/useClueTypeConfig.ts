import api from 'api';
import type { AxiosRequestConfig } from 'axios';
import { clueDebugLogger } from 'lib/utils/loggerUtil';
import { compileTypeDetectors, type TypeDetector } from 'lib/utils/typeDetection';
import { uniq } from 'lodash-es';
import isEmpty from 'lodash-es/isEmpty';
import { useEffect, useMemo, useState } from 'react';

/**
 * Hook to populate and provide the types detection and the available sources.
 * @param ready         Flag to signify if clue is ready to populate the types and sources.
 * @param baseURL       The base URL of the clue enrichment API.
 * @param debugLogging  Flag to toggle debug logging.
 * @param getToken      Callback to fetch the Bearer token.
 * @param onNetworkCall Callback to configure Axios requests.
 * @returns             An object containing the available sources and the types detection.
 */
const useClueTypeConfig = (
  ready: boolean,
  baseURL: string,
  debugLogging: boolean,
  getToken?: () => string,
  onNetworkCall?: (config: AxiosRequestConfig) => AxiosRequestConfig
): {
  availableSources: Array<string>;
  typesDetection: { [type: string]: RegExp };
  typeDetectors: TypeDetector[];
  supportedTypes: string[];
} => {
  // Initialize the sources and type detection for the user
  const [availableSources, setAvailableSources] = useState<string[]>([]);

  const [typeDetectors, setTypeDetectors] = useState<TypeDetector[]>([]);
  const typesDetection = useMemo(() => Object.fromEntries(typeDetectors), [typeDetectors]);
  const [supportedTypes, setSupportedTypes] = useState<string[]>([]);

  useEffect(() => {
    if (!ready) {
      return;
    }

    if (availableSources?.length > 0 && !isEmpty(typesDetection)) {
      return;
    }

    const headers: AxiosRequestConfig['headers'] = {};
    const token = getToken?.();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    // useEffect doesn't allow async functions to be used, so we wrap it in an IIFE
    (async () => {
      let requestConfig: AxiosRequestConfig = { baseURL, headers };
      if (onNetworkCall) {
        requestConfig = onNetworkCall(requestConfig);
      }

      clueDebugLogger('Executing types and type detection lookup', debugLogging);
      const [_typesPerSource, _typesDetections] = await Promise.all([
        api.lookup.types.get(requestConfig),
        api.v2.lookup.types_detection.get(requestConfig)
      ]);

      if (_typesPerSource) {
        setAvailableSources(Object.keys(_typesPerSource));
        setSupportedTypes(uniq(Object.values(_typesPerSource).flat()));
      }

      if (_typesDetections) {
        setTypeDetectors(compileTypeDetectors(_typesDetections));
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseURL, ready]);

  return {
    availableSources,
    typesDetection,
    typeDetectors,
    supportedTypes
  };
};

export default useClueTypeConfig;
