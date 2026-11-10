import api, { joinAllUri } from 'api';
import { uri } from 'api/sync';
import type { AxiosRequestConfig } from 'axios';
import { last } from 'lodash-es';
import type { DocumentsWithCheckpoint, ReplicationPullHandlerResult } from 'rxdb';
import { replicateRxCollection } from 'rxdb/plugins/replication';
import { Subject } from 'rxjs';
import { ClueReplicationError } from './errors';
import { REPLICATORS } from './globals';
import type { Checkpoint } from './sync';
import type { DatabaseConfig, SelectorCollection, SelectorDocType } from './types';

const DEFAULT_PULL_BATCH_SIZE = 250;

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
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let closed = false;
  const isClosed = () => closed || collection.closed;

  collection.onClose.push(() => {
    closed = true;
    if (retryTimer !== null) {
      clearTimeout(retryTimer);
      retryTimer = null;
    }
    currentXhr?.abort();
  });

  const reportHttpFailure = async (error: ClueReplicationError): Promise<boolean> => {
    if (!config.onReplicationError) {
      // eslint-disable-next-line no-console
      console.error(error);
      return false;
    }
    try {
      return (await config.onReplicationError(error)) === true;
    } catch (recoveryError) {
      // eslint-disable-next-line no-console
      console.error('Replication recovery failed', recoveryError);
      return false;
    }
  };

  const connect = (timeout = 1000, recoveredToken?: string) => {
    if (isClosed()) {
      return;
    }

    let lastProcessedIndex = 0;
    let done = false;
    const _xhr = new XMLHttpRequest();
    currentXhr = _xhr;

    const reconnect = () => {
      if (isClosed()) {
        return;
      }

      if (import.meta.env.MODE !== 'test') {
        // eslint-disable-next-line no-console
        console.log(`Retrying live connection in ${timeout}ms...`);
      }

      retryTimer = setTimeout(() => {
        retryTimer = null;
        // Exponential increase
        connect(Math.min(timeout * 2, MAX_RETRY_DELAY));
      }, timeout);
      if (collection.synced) {
        stream$.next('RESYNC');
      }
    };

    const fullUrl = (config.baseURL ?? '') + joinAllUri(uri(), collection.name, 'stream');
    _xhr.open('GET', fullUrl, true);

    _xhr.setRequestHeader('Accept', 'text/event-stream');

    const token = (recoveredToken ?? config.getToken?.())?.trim();
    if (token) {
      _xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

    const processLines = (flush = false) => {
      if (done || isClosed() || _xhr.status < 200 || _xhr.status >= 300) {
        return;
      }

      const lines = _xhr.responseText.slice(lastProcessedIndex).split('\n');
      lastProcessedIndex = _xhr.responseText.length - (flush ? 0 : (lines.pop()?.length ?? 0));

      for (const line of lines) {
        if (!line.trim()) {
          continue;
        }
        let event: EventStreamEntry;
        try {
          const parsed = JSON.parse(line);
          const lastUpdated = parsed?.checkpoint?.last_updated ?? parsed?.checkpoint?.updated_at;
          if (
            !Number.isFinite(parsed?.id) ||
            !Array.isArray(parsed.documents) ||
            (parsed.checkpoint !== null && (typeof parsed.checkpoint?.id !== 'string' || !Number.isFinite(lastUpdated)))
          ) {
            throw new Error('Invalid replication stream event');
          }
          event = {
            ...parsed,
            checkpoint: parsed.checkpoint === null ? null : { id: parsed.checkpoint.id, last_updated: lastUpdated }
          };
        } catch (error) {
          // eslint-disable-next-line no-console
          console.error('Invalid replication stream event', error);
          continue;
        }

        timeout = 1000;
        if (loggedEvents.includes(event.id)) {
          continue;
        }

        if (loggedEvents.length >= 1000) {
          loggedEvents.shift();
        }

        loggedEvents.push(event.id);
        stream$.next(event);
      }
    };

    const handleEnd = async () => {
      if (done || isClosed()) {
        return;
      }
      processLines(true);
      done = true;

      if (_xhr.status >= 400) {
        const error = new ClueReplicationError(_xhr.status, fullUrl, collection.name);
        if (_xhr.status >= 500) {
          void reportHttpFailure(error);
          reconnect();
        } else if (_xhr.status === 401) {
          if (await reportHttpFailure(error)) {
            const refreshedToken = config.getToken?.()?.trim();
            if (refreshedToken && refreshedToken !== token && !isClosed()) {
              connect(1000, refreshedToken);
              if (collection.synced) {
                stream$.next('RESYNC');
              }
            }
          }
        } else {
          void reportHttpFailure(error);
        }
        return;
      }
      reconnect();
    };

    _xhr.onload = () => void handleEnd();
    _xhr.onerror = () => void handleEnd();
    _xhr.onprogress = () => processLines();

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
  const pullBatchSize = config.pullBatchSize ?? DEFAULT_PULL_BATCH_SIZE;

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
      batchSize: pullBatchSize,
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

        if (result.length < pullBatchSize) {
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
