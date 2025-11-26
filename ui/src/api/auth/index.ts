import { joinUri, uri as parentUri } from 'api';
import * as login from 'api/auth/login';

export const uri = () => {
  return joinUri(parentUri(), 'auth');
};

export { login };
