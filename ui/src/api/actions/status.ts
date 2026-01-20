import { hget, joinUri } from 'api';
import type { AxiosRequestConfig } from 'axios';
import isNil from 'lodash-es/isNil';
import { uri } from '.';

export const get = (
  actionId: string,
  taskId: string,
  options: {
    timeout?: number;
  } = { timeout: null },
  config?: AxiosRequestConfig
) => {
  const searchParams: string[] = [];

  if (!isNil(options.timeout)) {
    searchParams.push(`max_timeout=${options.timeout}`);
  }

  return hget(
    joinUri(
      joinUri(uri(), actionId.replace('.', '/')),
      joinUri('status', taskId),
      searchParams.length > 0 ? new URLSearchParams(searchParams.join('&')) : null
    ),
    null,
    config
  );
};
