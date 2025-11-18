import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';
import axiosRetry, { exponentialDelay, isNetworkError } from 'axios-retry';
import type { ClueResponse } from 'lib/types/network';
import { getAxiosCache, setAxiosCache } from 'lib/utils/sessionStorage';

class AxiosCache {
  constructor(_axios: AxiosInstance) {
    _axios.interceptors.response.use(async res => {
      const cache = getAxiosCache();

      if (res.status >= 200 && res.status < 300 && res.headers.etag) {
        setAxiosCache(res.headers.etag, res.data);
      }

      if (res.status === 304) {
        const etag = res.config.headers['If-Match'] as string;
        if (etag) {
          res.data = cache[etag];
        }
      }

      return res;
    });
  }
}

export default class AxiosClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      validateStatus: status => (status >= 200 && status < 300) || status === 304
    });

    new AxiosCache(this.client);

    axiosRetry(this.client as any, {
      retries: 3,
      retryCondition: err => {
        return (
          // Don't retry 502s, as we assume the server handles retries in those cases
          isNetworkError(err) ||
          (err?.response?.status >= 500 && err?.response?.status !== 502) ||
          err?.response?.status === 429
        );
      },
      retryDelay: exponentialDelay
    });
  }

  public async fetch<R>(
    url: string,
    method: 'get' | 'post' | 'put' | 'delete' | 'patch' = 'get',
    body?: any,
    params?: URLSearchParams,
    axiosConfig?: AxiosRequestConfig
  ): Promise<[ClueResponse<R>, number, { [index: string]: any }]> {
    const config: AxiosRequestConfig = {
      url,
      params,
      method,
      withCredentials: true,
      data: JSON.stringify(body),
      ...(axiosConfig ?? {})
    };

    try {
      const response = await this.client(config);

      return [response.data, response.status, response.headers];
    } catch (e) {
      if (e instanceof AxiosError && e.response?.data) {
        return [e.response.data, e.response.status, e.response.headers];
      }

      throw e;
    }
  }
}
