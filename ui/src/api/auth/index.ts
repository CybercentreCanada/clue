import { joinUri, uri as parentUri } from 'api';
import * as login from 'api/auth/login';
import * as refresh from 'api/auth/refresh';

export const uri = () => {
  return joinUri(parentUri(), 'auth');
};

export { login, refresh };
