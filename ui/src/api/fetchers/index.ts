import { hget, hpost, joinAllUri, joinUri, uri as parentUri } from 'api';
import type { AxiosRequestConfig } from 'axios';
import type { FetcherDefinitionsResponse, FetcherResult } from 'lib/types/fetcher';
import type { Selector } from 'lib/types/lookup';

export function uri() {
  return joinUri(parentUri(), 'fetchers');
}
export function get(config?: AxiosRequestConfig): Promise<FetcherDefinitionsResponse> {
  return hget(uri(), null, config);
}

export function post(fetcherId: string, selector: Selector, config?: AxiosRequestConfig): Promise<FetcherResult> {
  return hpost(joinAllUri(uri(), fetcherId.replace('.', '/')), selector, config);
}
