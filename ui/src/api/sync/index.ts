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
  collection: string,
  id?: string,
  timestamp?: number,
  omitDeleted?: boolean,
  config?: AxiosRequestConfig
): Promise<SyncResponse<T>> => {
  const params = new URLSearchParams();

  params.set('limit', '250');

  if (!isNil(id)) {
    params.set('id', id.toString());
  }

  if (!isNil(timestamp)) {
    params.set('updated_at', timestamp.toString());
  }

  if (!isNil(omitDeleted) && omitDeleted) {
    params.set('omit_deleted', 'true');
  }

  return hget(joinAllUri(uri(), collection), params, config);
};

const post = <T>(
  collection: string,
  payload: PushPayload<T>,
  config?: AxiosRequestConfig
): Promise<WithDeleted<WithLastUpdated<T>>[]> => {
  return hpost(joinAllUri(uri(), collection), payload, config);
};

export { get, post, uri };
