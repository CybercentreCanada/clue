import { hget, joinUri } from 'api';
import { uri as parentUri } from 'api/actions';
import type { AxiosRequestConfig } from 'axios';
import type { FetcherResult } from 'lib/main';

import isNil from 'lodash-es/isNil';

export const get = (
  fetcherId: string,
  taskId: string,
  options: {
    timeout?: number;
  } = { timeout: null },
  config?: AxiosRequestConfig
): Promise<FetcherResult> => {
  const searchParams: string[] = [];

  if (!isNil(options.timeout)) {
    searchParams.push(`max_timeout=${options.timeout}`);
  }

  return hget<FetcherResult>(
    joinUri(parentUri(), `${fetcherId.replace('.', '/')}/status/${taskId}`),
    searchParams.length > 0 ? new URLSearchParams(searchParams.join('&')) : null,
    config
  );
};
