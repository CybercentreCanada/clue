import { hpost, joinUri } from 'api';
import { uri as parentUri } from 'api/auth';
import type { LoginResponse } from 'api/auth/login';

export type PostRefreshBody = {
  provider: string;
  refresh_token: string;
};

export const uri = () => {
  return joinUri(parentUri(), 'refresh');
};

/**
 * Exchange a stored refresh token for new credentials. The body contains only the provider and the refresh token.
 */
export const post = ({ provider, refresh_token }: PostRefreshBody): Promise<LoginResponse> => {
  return hpost(uri(), { provider, refresh_token });
};
