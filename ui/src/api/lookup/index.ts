import { joinUri, uri as parentUri } from 'api';
import * as enrich from 'api/lookup/enrich';
import * as types from 'api/lookup/types';
import * as types_detection from 'api/lookup/types_detection';

export const uri = () => {
  return joinUri(parentUri(), 'lookup');
};

export { enrich, types, types_detection };
