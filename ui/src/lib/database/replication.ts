import api from 'api';
import { last } from 'lodash-es';
import { replicateRxCollection } from 'rxdb/plugins/replication';
import { SyncResponse } from './sync';
import { SelectorCollection, SelectorDocType } from './types';

export const replicateSelectorCollection = async (baseURL: string, collection: SelectorCollection) => {
  return replicateRxCollection<SelectorDocType, SyncResponse['checkpoint']>({
    collection,
    replicationIdentifier: `clue-replication-${collection.name}-${baseURL}`,
    push: {
      handler: async docs => api.sync.post<SelectorDocType>('selector', docs),
      batchSize: 50
    },
    pull: {
      handler: async lastCheckpoint => {
        const minTimestamp = lastCheckpoint ? lastCheckpoint.lastUpdated : 0;

        const result = await api.sync.get('selector', minTimestamp);

        return {
          documents: result.documents,
          checkpoint:
            result.documents.length < 1
              ? lastCheckpoint
              : {
                  id: last(result.documents).id,
                  lastUpdated: last(result.documents).lastUpdated
                }
        };
      }
    }
  });
};
