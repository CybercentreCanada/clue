import { hget, hpost, joinAllUri, joinUri, uri as parentUri } from 'api';
import type { AxiosRequestConfig } from 'axios';
import type { PushPayload, SyncResponse } from 'lib/database/sync';
import type { WithLastUpdated } from 'lib/database/types';
import { isNil } from 'lodash-es';
import type { WithDeleted } from 'rxdb';

const uri = () => {
  return joinUri(parentUri(), 'sync');
};

const get = <T>(
  collection: 'selector' | 'status',
  id: string,
  timestamp: number,
  config?: AxiosRequestConfig
): Promise<SyncResponse<T>> => {
  const params = new URLSearchParams();

  params.set('limit', '250');

  if (!isNil(timestamp)) {
    params.set('updated_at', timestamp.toString());
  }

  if (!isNil(id)) {
    params.set('id', id.toString());
  }

  return hget(joinAllUri(uri(), collection), params, config);
};

const post = <T>(
  collection: 'selector' | 'status',
  payload: PushPayload<T>,
  config?: AxiosRequestConfig
): Promise<WithDeleted<WithLastUpdated<T>>[]> => {
  return hpost(joinAllUri(uri(), collection), payload, config);
};

export { get, post, uri };
