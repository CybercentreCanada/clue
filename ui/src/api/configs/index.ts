import { hget, joinUri, uri as parentUri } from 'api';
import type { AxiosRequestConfig } from 'axios';
import type { ApiType } from 'lib/types/config';

const uri = () => {
  return joinUri(parentUri(), 'configs');
};

const get = (config?: AxiosRequestConfig): Promise<ApiType> => {
  return hget(uri(), null, config);
};

export { get, uri };
