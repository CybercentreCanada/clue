import { hget, hpost, joinUri, uri as parentUri } from 'api';
import type { AxiosRequestConfig } from 'axios';
import type { ActionDefinitionsResponse, ActionResult } from 'lib/types/action';
import type { Selector } from 'lib/types/lookup';
import isNil from 'lodash-es/isNil';

export const uri = () => {
  return joinUri(parentUri(), 'actions');
};

export const get = (config?: AxiosRequestConfig): Promise<ActionDefinitionsResponse> => {
  return hget(uri(), null, config);
};

export const post = (
  actionId: string,
  selectors: Selector | Selector[],
  params: { [index: string]: any },
  options: {
    timeout?: number;
  } = { timeout: null },
  config?: AxiosRequestConfig
): Promise<ActionResult> => {
  const searchParams: string[] = [];

  if (!isNil(options.timeout)) {
    searchParams.push(`max_timeout=${options.timeout}`);
  }

  const payload = { ...params };
  if (!Array.isArray(selectors)) {
    payload.selector = selectors;
    payload.selectors = [];
  } else if (selectors.length < 2) {
    payload.selector = selectors[0];
    payload.selectors = [];
  } else {
    payload.selectors = selectors;
  }

  return hpost(
    joinUri(
      joinUri(uri(), 'execute'),
      actionId.replace('.', '/'),
      searchParams.length > 0 ? new URLSearchParams(searchParams.join('&')) : null
    ),
    payload,
    config
  );
};
