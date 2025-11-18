import { joinUri, uri as parentUri } from 'api';
import * as login from 'api/auth/login';

export function uri() {
  return joinUri(parentUri(), 'auth');
}

export { login };
