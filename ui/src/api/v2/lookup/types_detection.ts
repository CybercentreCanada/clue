import { hget, joinUri } from 'api';
import { uri as parentUri } from 'api/v2/lookup';
import type { AxiosRequestConfig } from 'axios';
import type { TypesDetectionV2Response } from 'lib/types/lookup';

export const uri = () => joinUri(parentUri(), 'types_detection');

export const get = (config?: AxiosRequestConfig): Promise<TypesDetectionV2Response> => {
  return hget(uri(), null, config);
};
