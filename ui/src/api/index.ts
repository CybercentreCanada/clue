import * as actions from 'api/actions';
import * as auth from 'api/auth';
import * as configs from 'api/configs';
import * as fetchers from 'api/fetchers';
import * as lookup from 'api/lookup';
import * as _static from 'api/static';
import type { AxiosRequestConfig, RawAxiosRequestHeaders } from 'axios';
import type { ClueResponse } from 'lib/types/network';
import { StorageKey } from 'lib/utils/constants';
import AxiosClient from 'rest/AxiosClient';
import type { URLSearchParams } from 'url';
import urlJoin from 'url-join';
import {
  getStored as getLocalStored,
  removeStored as removeLocalStored,
  saveLoginCredential,
  setStored as setLocalStored
} from 'utils/localStorage';
import getXSRFCookie from 'utils/xsrf';

/**
 * Concrete Rest HTTP client implementation.
 */
const client = new AxiosClient();

/**
 * Defining the default export exposing all children routes of '/api/v1/'.
 */
// prettier-ignore
const api = {
  auth,
  configs,
  lookup,
  actions,
  fetchers,
  _static
};

/**
 * The base section of the Clue API uri.
 *
 * `/api/v1/`
 */
export const uri = () => {
  return '/api/v1';
};

/**
 * Format/Adapt the specified URI to an Clue API uri.
 *
 * Ensure it starts with '/api/v1' and doesn't end with a '/'.
 *
 * @param _uri - the uri to format.
 * @returns `string` - properly formatted clue uri.
 */
const format = (_uri: string, baseURL?: string): string => {
  const path = _uri.startsWith(uri()) ? _uri : `${uri()}/${_uri.replace(/\/$/, '')}`.replace('//', '/');

  return baseURL ? baseURL + path : path;
};

/**
 * Append series of search parameters to the specified uri.
 *
 * @param _uri - the base uri.
 * @param searchParams  -  a list of search parameters to join with the uri.
 * @returns a uri with the search parameters.
 */
export const joinParams = (_uri: string, searchParams?: URLSearchParams): string => {
  return `${_uri}${searchParams ? `${_uri.indexOf('?') > 0 ? '&' : '?'}${searchParams.toString()}` : ''}`;
};

/**
 * Join two uri and then join them with the specified search parameters.
 *
 * This function will format the resulting uri section using {@link format}.
 *
 * This function will join the specified parameters using {@link joinParams}
 *
 * @param uri1 the first section of the uri.
 * @param uri2 the second section of the uri.
 * @param searchParams the search parameters to append to the uri.
 * @returns a uri that joins `uri1` and `uri2` with the specified `_search` parameters.
 */
export const joinUri = (uri1: string, uri2: string, searchParams?: URLSearchParams): string => {
  const _uri = format(urlJoin(uri1, uri2));
  return searchParams ? joinParams(_uri, searchParams) : _uri;
};

/**
 * joinUrl all params together
 *
 * @returns a uri generated from all params
 */
export const joinAllUri = (...urlParts: string[]): string => {
  return urlJoin(...urlParts);
};

/**
 * Create the required headers object for attaching to the request
 *
 * @param ifMatch a value for the If-Match header
 */
export const setHeaders = (ifMatch?: string): HeadersInit => {
  const headers: HeadersInit = {};
  if (ifMatch) {
    headers['If-Match'] = ifMatch;
  }
  return headers;
};

/**
 * Generic fetch implementation for Clue API.
 *
 * This function will format the specified `url` with {@link format} before issuing the fetch.
 *
 * @param _uri - the uri to fetch.
 * @param method - the http method to use.
 * @param body - the body of the request.
 * @returns the `api_response` object of the returned {@link ClueResponse}.
 */
export const hfetch = async <R>(
  _uri: string,
  method: 'get' | 'post' | 'put' | 'delete' | 'patch' = 'get',
  body?: any,
  searchParams?: URLSearchParams,
  axiosConfig?: AxiosRequestConfig
): Promise<R> => {
  const authToken = getLocalStored(StorageKey.APP_TOKEN);

  const config: AxiosRequestConfig = {
    ...(axiosConfig ?? {}),
    headers: {
      ...(axiosConfig?.headers ?? {}),
      'Content-Type': 'application/json',
      'X-XSRF-TOKEN': getXSRFCookie()
    } as RawAxiosRequestHeaders
  };

  // Set the token if it exists and hasn't already been set
  if (authToken && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${authToken}`;
  }

  // Wait for it ....
  const [json, statusCode] = await client.fetch<ClueResponse<R>>(
    format(_uri, config.baseURL),
    method,
    body,
    searchParams,
    config
  );

  if (!json) {
    return null;
  }

  // Did it work?
  if (statusCode < 300 || statusCode === 304) {
    return json.api_response as R;
  }

  if (statusCode === 401) {
    if (!getLocalStored(StorageKey.NEXT_LOCATION)) {
      setLocalStored(StorageKey.NEXT_LOCATION, window.location.pathname);
      setLocalStored(StorageKey.NEXT_SEARCH, window.location.search);
    }

    if (!_uri.includes('/auth/login') && getLocalStored(StorageKey.REFRESH_TOKEN)) {
      //Refresh access token if possible
      //And re-execute the previous api call (seamless)
      const refreshToken: string = getLocalStored(StorageKey.REFRESH_TOKEN);
      const provider: string = getLocalStored(StorageKey.PROVIDER);
      const refreshResponse = await api.auth.login.post({
        refresh_token: refreshToken,
        provider: provider
      });

      if (refreshResponse) {
        saveLoginCredential(refreshResponse);
        const result = await hfetch<R>(_uri, method, body, searchParams);

        removeLocalStored(StorageKey.NEXT_LOCATION);
        removeLocalStored(StorageKey.NEXT_SEARCH);

        return result;
      }
    }

    saveLoginCredential({});

    return;
  }

  // Throw it back.
  throw new Error(
    json.api_error_message || (json as unknown as string) || `Error while fetching ${_uri} - ${method.toUpperCase()}`,
    {
      cause: json
    }
  );
};

/**
 * Perform an HTTP GET for the specified uri.
 *
 * This method eventually delegates to {@link hfetch}
 *
 * @param _uri - the uri to fetch.
 * @returns the `api_response` object of the returned {@link ClueResponse}.
 */
export const hget = <R = any>(
  _uri: string,
  searchParams?: URLSearchParams,
  config: AxiosRequestConfig = {}
): Promise<R> => {
  return hfetch<R>(_uri, 'get', null, searchParams, config);
};

/**
 * Perform an HTTP POST for the specified uri and body data.
 *
 * This method eventually delegates to {@link hfetch}
 *
 * @param _uri - the uri to fetch.
 * @param body - the body of the request.
 * @returns the `api_response` object of the returned {@link ClueResponse}.
 */
export const hpost = <R = any>(_uri: string, body: any, config: AxiosRequestConfig = {}): Promise<R> => {
  return hfetch<R>(_uri, 'post', body, undefined, config);
};

/**
 * Peform an HTTP PUT for the specified uri and body data.
 *
 * This method eventually delegates to {@link hfetch}
 *
 * @param _uri - the uri to fetch.
 * @param body - the body of the request.
 * @returns the `api_response` object of the returned {@link ClueResponse}.
 */
export const hput = <R = any>(_uri: string, body: any, config: AxiosRequestConfig = {}): Promise<R> => {
  return hfetch<R>(_uri, 'put', body, undefined, config);
};

/**
 * Peform an HTTP PATCH for the specified uri and body data.
 *
 * This method eventually delegates to {@link hfetch}
 *
 * @param _uri - the uri to fetch.
 * @param body - the body of the request.
 * @returns the `api_response` object of the returned {@link ClueResponse}.
 */
export const hpatch = <R = any>(_uri: string, body: any, config: AxiosRequestConfig = {}): Promise<R> => {
  return hfetch<R>(_uri, 'patch', body, undefined, config);
};

/**
 * Performa an HTTP DELETE for the specified uri.
 *
 * This method eventually delegates to {@link hfetch}
 *
 * @param _uri - the uri to fetch.
 * @returns the `api_response` object of the returned {@link ClueResponse}.
 */
export const hdelete = <R = any>(_uri: string, body = null, config: AxiosRequestConfig = {}): Promise<R> => {
  return hfetch<R>(_uri, 'delete', body, undefined, config);
};

/**
 * Default export exposing the clue rest api
 */
export default api;
