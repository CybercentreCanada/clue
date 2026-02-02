import { hget, hpost, joinAllUri, joinUri, uri as parentUri } from 'api';
import type { AxiosRequestConfig } from 'axios';
import { PushPayload, SyncResponse } from 'lib/database/sync';
import { isNil } from 'lodash-es';

const uri = () => {
  return joinUri(parentUri(), 'sync');
};

const get = (
  collection: 'selector' | 'status',
  timestamp: number,
  config?: AxiosRequestConfig
): Promise<SyncResponse> => {
  const params = new URLSearchParams();
  if (!isNil(timestamp)) {
    params.set('timestamp', timestamp.toString());
  }

  return hget(joinAllUri(uri(), collection), params, config);
};

const post = <T>(
  collection: 'selector' | 'status',
  payload: PushPayload<T>,
  config?: AxiosRequestConfig
): Promise<PushPayload<T>> => {
  return hpost(joinAllUri(uri(), collection), payload, config);
};

export { get, post, uri };
