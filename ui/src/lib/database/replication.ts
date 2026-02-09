import api from 'api';
import { last } from 'lodash-es';
import type { ReplicationPullHandlerResult } from 'rxdb';
import { replicateRxCollection } from 'rxdb/plugins/replication';
import type { Checkpoint } from './sync';
import type { SelectorCollection, SelectorDocType } from './types';

export const replicateSelectorCollection = async (collection: SelectorCollection) => {
  const replicationState = replicateRxCollection<SelectorDocType, Checkpoint>({
    collection,
    replicationIdentifier: `clue-replication-${collection.name}`,
    live: true,
    retryTime: 5000,
    waitForLeadership: false,
    push: {
      batchSize: 50,
      handler: async docs => {
        console.log(`Synchronizing ${docs.length} docs`);

        return api.sync.post<SelectorDocType>('selector', docs);
      }
    },
    pull: {
      batchSize: 250,
      handler: async (
        lastCheckpoint: Checkpoint
      ): Promise<ReplicationPullHandlerResult<SelectorDocType, Checkpoint>> => {
        const id = lastCheckpoint ? lastCheckpoint.id : null;
        const minTimestamp = lastCheckpoint ? lastCheckpoint.last_updated : 0;

        const result = await api.sync.get<SelectorDocType>('selector', id, minTimestamp);

        return {
          documents: result,
          checkpoint:
            result.length < 1
              ? null
              : {
                  id: last(result).id,
                  last_updated: last(result).updated_at
                }
        };
      }
    }
  });

  // eslint-disable-next-line no-console
  replicationState.error$.subscribe(err => console.error(err));

  return replicationState;
};
