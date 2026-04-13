import api, { joinAllUri } from 'api';
import { uri } from 'api/sync';
import type { AxiosRequestConfig } from 'axios';
import { last } from 'lodash-es';
import type { DocumentsWithCheckpoint, ReplicationPullHandlerResult } from 'rxdb';
import { replicateRxCollection } from 'rxdb/plugins/replication';
import { Subject } from 'rxjs';
import { REPLICATORS } from './globals';
import type { Checkpoint } from './sync';
import type { DatabaseConfig, SelectorCollection, SelectorDocType } from './types';

const PULL_BATCH_SIZE = 250;

const buildRequestConfig = (config: DatabaseConfig): AxiosRequestConfig => {
  const headers: AxiosRequestConfig['headers'] = {};
  const token = config.getToken?.();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let requestConfig: AxiosRequestConfig = { headers };
  if (config.baseURL) {
    requestConfig.baseURL = config.baseURL;
  }

  if (config.onNetworkCall) {
    requestConfig = config.onNetworkCall(requestConfig);
  }

  return requestConfig;
};

interface EventStreamEntry extends DocumentsWithCheckpoint<SelectorDocType, Checkpoint> {
  id: number;
}

const stream = (collection: SelectorCollection, config: DatabaseConfig) => {
  const stream$ = new Subject<EventStreamEntry | 'RESYNC'>();
  const MAX_RETRY_DELAY = 60000; // Cap at 60 seconds

  const loggedEvents: number[] = [];

  let currentXhr: XMLHttpRequest | null = null;
  collection.onClose.push(() => {
    currentXhr?.abort();
  });

  const connect = (timeout = 1000) => {
    let lastProcessedIndex = 0;
    const _xhr = new XMLHttpRequest();
    currentXhr = _xhr;

    const reconnect = () => {
      // eslint-disable-next-line no-console
      if (collection.closed) {
        return;
      }

      // eslint-disable-next-line no-console
      console.log(`Retrying live connection in ${timeout}ms...`);

      setTimeout(() => {
        // Exponential increase
        connect(Math.min(timeout * 2, MAX_RETRY_DELAY));
      }, timeout);
    };

    const fullUrl = (config.baseURL ?? '') + joinAllUri(uri(), collection.name, 'stream');
    _xhr.open('GET', fullUrl, true);

    _xhr.setRequestHeader('Accept', 'text/event-stream');

    const token = config.getToken?.();
    if (token) {
      _xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

    _xhr.onload = () => {
      reconnect();
      if (collection.synced) {
        stream$.next('RESYNC');
      }
    };

    _xhr.onerror = () => {
      // eslint-disable-next-line @typescript-eslint/no-use-before-define
      reconnect();
      if (collection.synced) {
        stream$.next('RESYNC');
      }
    };

    _xhr.onprogress = () => {
      if (_xhr.responseText) {
        timeout = 1000;
      }

      const newText = _xhr!.responseText.substring(lastProcessedIndex);
      const lines = newText
        .split('\n')
        .map(line => line.trim())
        .filter(line => !!line);

      try {
        for (const line of lines) {
          const event: EventStreamEntry = JSON.parse(line);

          if (loggedEvents.includes(event.id)) {
            continue;
          }

          // Ensure the list of events doesn't grow too large
          if (loggedEvents.length > 1000) {
            loggedEvents.shift();
          }

          loggedEvents.push(event.id);
          stream$.next(event);
        }
      } catch {
        return;
      }

      lastProcessedIndex = _xhr!.responseText.length;
    };

    _xhr.send();
  };

  connect();

  return stream$;
};

export const replicateSelectorCollection = async (
  replicationId: string,
  collection: SelectorCollection,
  config: DatabaseConfig
) => {
  collection.onClose.push(() => {
    delete REPLICATORS[replicationId];
  });

  const pullStream$ = stream(collection, config);

  const replicationState = replicateRxCollection<SelectorDocType, Checkpoint>({
    collection,
    replicationIdentifier: `clue-replication-${collection.name}`,
    autoStart: false,
    live: true,
    retryTime: 10000,
    waitForLeadership: false,
    push: {
      batchSize: 50,
      handler: async docs => api.sync.post<SelectorDocType>(collection.name, docs, buildRequestConfig(config))
    },
    pull: {
      batchSize: PULL_BATCH_SIZE,
      handler: async (
        lastCheckpoint: Checkpoint
      ): Promise<ReplicationPullHandlerResult<SelectorDocType, Checkpoint>> => {
        const id = lastCheckpoint ? lastCheckpoint.id : null;
        const minTimestamp = lastCheckpoint ? lastCheckpoint.last_updated : 0;

        const result = await api.sync.get<SelectorDocType>(
          collection.name,
          id,
          minTimestamp,
          !lastCheckpoint,
          buildRequestConfig(config)
        );

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
      },
      stream$: pullStream$.asObservable()
    }
  });

  // eslint-disable-next-line no-console
  replicationState.error$.subscribe(err => console.error(err));

  return replicationState;
};
