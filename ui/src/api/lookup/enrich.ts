import { hpost, joinUri } from 'api';
import { uri as parentUri } from 'api/lookup';
import type { AxiosRequestConfig } from 'axios';
import type { BulkEnrichResponses, Selector } from 'lib/types/lookup';
import isNil from 'lodash-es/isNil';

export const uri = () => {
  return joinUri(parentUri(), 'enrich');
};

export const post = (
  bulkData: Selector[],
  sources: string[] = [],
  options: {
    classification?: string;
    timeout?: number;
    includeRaw?: boolean;
    noCache?: boolean;
  } = { timeout: null, includeRaw: false, noCache: false },
  config?: AxiosRequestConfig
): Promise<BulkEnrichResponses> => {
  const searchParams: string[] = [];

  if (sources?.length > 0) {
    searchParams.push(`sources=${sources.join()}`);
  }

  if (options.classification) {
    searchParams.push(`classification=${encodeURIComponent(options.classification)}`);
  }

  if (!isNil(options.timeout)) {
    searchParams.push(`max_timeout=${options.timeout}`);
  }

  if (options.includeRaw) {
    searchParams.push('include_raw=true');
  }

  if (options.noCache) {
    searchParams.push('no_cache=true');
  }

  return hpost(
    joinUri(uri(), '', searchParams.length > 0 ? new URLSearchParams(searchParams.join('&')) : null),
    bulkData,
    config
  );
};
