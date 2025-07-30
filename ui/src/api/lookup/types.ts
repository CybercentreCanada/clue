import { hget, joinUri } from 'api';
import { uri as parentUri } from 'api/lookup';
import type { AxiosRequestConfig } from 'axios';
import type { TypesResponse } from 'lib/types/lookup';

export function uri() {
  return joinUri(parentUri(), 'types');
}

export function get(config?: AxiosRequestConfig): Promise<TypesResponse> {
  return hget(uri(), null, config);
}
