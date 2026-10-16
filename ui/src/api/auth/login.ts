import { hget, hpost, joinUri } from 'api';
import { uri as parentUri } from 'api/auth';
import type { ClueUser } from 'models/entities/ClueUser';
import { buildOAuthCallbackParams } from 'utils/oauth';

export type PostLoginBody = {
  user?: string;
  password?: string;
  provider?: string;
};

export type LoginResponse = {
  app_token?: string;
  refresh_token?: string;
  provider?: string;
  user?: ClueUser;
};

export const uri = (searchParams?: URLSearchParams) => {
  return joinUri(parentUri(), 'login', searchParams);
};

export const post = (body: PostLoginBody): Promise<LoginResponse> => {
  return hpost(uri(), body);
};

/**
 * Redeem an OAuth authorization-code callback. Only allowlisted callback parameters are forwarded.
 */
export const get = (search: URLSearchParams): Promise<LoginResponse> => {
  return hget(uri(), buildOAuthCallbackParams(search));
};
