import { hget, joinUri, uri as parentUri } from 'api';
import type { AxiosRequestConfig } from 'axios';
import type { ApiType } from 'lib/types/config';

export function uri() {
  return joinUri(parentUri(), 'configs');
}

export function get(config?: AxiosRequestConfig): Promise<ApiType> {
  return hget(uri(), null, config);
}
