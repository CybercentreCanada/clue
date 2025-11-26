import { hget, hpost, joinAllUri, joinUri, uri as parentUri } from 'api';
import type { AxiosRequestConfig } from 'axios';
import type { FetcherDefinitionsResponse, FetcherResult } from 'lib/types/fetcher';
import type { Selector } from 'lib/types/lookup';

const uri = () => {
  return joinUri(parentUri(), 'fetchers');
};
const get = (config?: AxiosRequestConfig): Promise<FetcherDefinitionsResponse> => {
  return hget(uri(), null, config);
};

const post = (fetcherId: string, selector: Selector, config?: AxiosRequestConfig): Promise<FetcherResult> => {
  return hpost(joinAllUri(uri(), fetcherId.replace('.', '/')), selector, config);
};

export { get, post, uri };
