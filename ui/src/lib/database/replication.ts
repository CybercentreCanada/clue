import api from 'api';
import { last } from 'lodash-es';
import type { ReplicationPullHandlerResult } from 'rxdb';
import { replicateRxCollection } from 'rxdb/plugins/replication';
import type { Checkpoint } from './sync';
import type { SelectorCollection, SelectorDocType } from './types';

const PULL_BATCH_SIZE = 250;

export const replicateSelectorCollection = async (collection: SelectorCollection) => {
  const pullStream$ = api.sync.stream(collection);

  const replicationState = replicateRxCollection<SelectorDocType, Checkpoint>({
    collection,
    replicationIdentifier: `clue-replication-${collection.name}`,
    live: true,
    retryTime: 5000,
    waitForLeadership: false,
    push: {
      batchSize: 50,
      handler: async docs => {
        try {
          return await api.sync.post<SelectorDocType>('selector', docs);
        } catch {
          return [];
        }
      }
    },
    pull: {
      batchSize: PULL_BATCH_SIZE,
      handler: async (
        lastCheckpoint: Checkpoint
      ): Promise<ReplicationPullHandlerResult<SelectorDocType, Checkpoint>> => {
        const id = lastCheckpoint ? lastCheckpoint.id : null;
        const minTimestamp = lastCheckpoint ? lastCheckpoint.last_updated : 0;

        // Retry indefinitely with exponential backoff + jitter until the network call succeeds.
        const maxDelay = 30_000; // maximum backoff delay in ms
        let attempt = 0;

        while (true) {
          try {
            const result = await api.sync.get<SelectorDocType>('selector', id, minTimestamp);

            if (result.length < PULL_BATCH_SIZE) {
              collection.synced = true;
            }

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
          } catch {
            // Increase attempt count and compute exponential backoff with jitter.
            attempt += 1;
            const base = Math.min(1000 * 2 ** (attempt - 1), maxDelay);
            // jitter between base/2 and base
            const jitter = Math.floor(Math.random() * (base / 2));
            const waitMs = Math.floor(base / 2) + jitter;

            // Log and wait, then retry. Never rethrow so the replication keeps trying.
            // eslint-disable-next-line no-console
            console.log(`Replication pull failed (attempt ${attempt}), retrying in ${waitMs}ms`);
            await new Promise(resolve => setTimeout(resolve, waitMs));
          }
        }
      },
      stream$: pullStream$.asObservable()
    }
  });

  // eslint-disable-next-line no-console
  replicationState.error$.subscribe(err => console.error(err));

  return replicationState;
};
