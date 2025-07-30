import { hget, joinUri } from 'api';
import { uri as parentUri } from 'api/lookup';
import type { AxiosRequestConfig } from 'axios';
import type { TypesDetectionResponse } from 'lib/types/lookup';

export function uri() {
  return joinUri(parentUri(), 'types_detection');
}

export function get(config?: AxiosRequestConfig): Promise<TypesDetectionResponse> {
  return hget(uri(), null, config);
}
