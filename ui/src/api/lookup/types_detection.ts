import { hget, joinUri } from 'api';
import { uri as parentUri } from 'api/lookup';
import type { AxiosRequestConfig } from 'axios';
import type { TypesDetectionResponse } from 'lib/types/lookup';

export const uri = () => {
  return joinUri(parentUri(), 'types_detection');
};

export const get = (config?: AxiosRequestConfig): Promise<TypesDetectionResponse> => {
  return hget(uri(), null, config);
};
