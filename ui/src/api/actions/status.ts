import { hget, joinUri } from 'api';
import { uri as parentUri } from 'api/actions';
import type { AxiosRequestConfig } from 'axios';
import type { ActionResult } from 'lib/types/action';
import type { WithActionData } from 'lib/types/WithActionData';

import isNil from 'lodash-es/isNil';

export const get = (
  actionId: string,
  taskId: string,
  options: {
    timeout?: number;
  } = { timeout: null },
  config?: AxiosRequestConfig
): Promise<WithActionData<ActionResult>> => {
  const searchParams: string[] = [];

  if (!isNil(options.timeout)) {
    searchParams.push(`max_timeout=${options.timeout}`);
  }

  return hget<WithActionData<ActionResult>>(
    joinUri(
      parentUri(),
      `${actionId.replace('.', '/')}/status/${taskId}`,
      searchParams.length > 0 ? new URLSearchParams(searchParams.join('&')) : null
    ),

    null,
    config
  );
};
