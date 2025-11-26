import { hget, joinAllUri } from 'api';
import { uri as parentUri } from 'api/static';
import type { AxiosRequestConfig } from 'axios';

export type DocumentationResponse = { [type: string]: string };

export const uri = (file: string) => {
  return joinAllUri(parentUri(), 'docs', file);
};

export const get = (file: string, config?: AxiosRequestConfig): Promise<DocumentationResponse> => {
  return hget(uri(file), null, config);
};
