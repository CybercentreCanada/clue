import { hget, joinUri } from 'api';
import { uri as parentUri } from 'api/static';
import type { AxiosRequestConfig } from 'axios';

export type DocumentationResponse = { [type: string]: string };

export const uri = (filter?: string) => {
  return joinUri(parentUri(), filter ? '/docs?filter=' + filter : '/docs');
};

export const get = (filter?: string, config?: AxiosRequestConfig): Promise<DocumentationResponse> => {
  return hget(uri(filter), null, config);
};
