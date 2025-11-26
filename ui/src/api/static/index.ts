import { joinUri, uri as parentUri } from 'api';
import * as all_documentation from 'api/static/all_documentation';
import * as documentation from 'api/static/documentation';

export const uri = () => {
  return joinUri(parentUri(), 'static');
};

export { all_documentation, documentation };
