import { joinUri } from 'api';
import { uri as parentUri } from 'api/v2';
import * as types_detection from 'api/v2/lookup/types_detection';

export const uri = () => {
  return joinUri(parentUri(), 'lookup');
};

export { types_detection };
