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

const parseStreamEvent = (line: string): EventStreamEntry | null => {
  try {
    const event = JSON.parse(line);
    const lastUpdated = event?.checkpoint?.last_updated ?? event?.checkpoint?.updated_at;
    const checkpoint =
      event?.checkpoint === null
        ? null
        : typeof event?.checkpoint?.id === 'string' && Number.isFinite(lastUpdated)
          ? { id: event.checkpoint.id, last_updated: lastUpdated }
          : undefined;

    if (!Number.isFinite(event?.id) || !Array.isArray(event.documents) || checkpoint === undefined) {
      return null;
    }

    return { ...event, checkpoint };
  } catch {
    return null;
  }
};

const stream = (collection: SelectorCollection, config: DatabaseConfig) => {
  const stream$ = new Subject<EventStreamEntry | 'RESYNC'>();
  const MAX_RETRY_DELAY = 60000; // Cap at 60 seconds
  const INITIAL_RETRY_DELAY = 1000;

  const loggedEvents: number[] = [];
  let currentXhr: XMLHttpRequest | null = null;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let closed = false;

  const isClosed = () => closed || collection.closed;
  const getToken = () => {
    try {
      return config.getToken?.();
    } catch {
      return undefined;
    }
  };

  const reportHttpFailure = async (error: ClueReplicationError): Promise<boolean> => {
    try {
      if (!config.onReplicationError) {
        // eslint-disable-next-line no-console
        console.error(error);
        return false;
      }

      return (await config.onReplicationError(error)) === true;
    } catch {
      return false;
    }
  };

  const emitResyncIfNeeded = () => {
    if (!isClosed() && collection.synced) {
      stream$.next('RESYNC');
    }
  };

  const connect = (timeout = INITIAL_RETRY_DELAY, token = getToken()) => {
    if (isClosed()) {
      return;
    }

    let lastProcessedIndex = 0;
    let done = false;
    const xhr = new XMLHttpRequest();
    currentXhr = xhr;

    const fullUrl = (config.baseURL ?? '') + joinAllUri(uri(), collection.name, 'stream');
    xhr.open('GET', fullUrl, true);
    xhr.setRequestHeader('Accept', 'text/event-stream');
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

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
        connect(Math.min(timeout * 2, MAX_RETRY_DELAY));
      }, timeout);
      emitResyncIfNeeded();
    };

    const processLines = (flush = false) => {
      if (done || isClosed() || xhr.status < 200 || xhr.status >= 300) {
        return;
      }

      const lines = xhr.responseText.slice(lastProcessedIndex).split('\n');
      lastProcessedIndex = xhr.responseText.length - (flush ? 0 : (lines.pop()?.length ?? 0));

      for (const line of lines) {
        const event = line.trim() ? parseStreamEvent(line) : null;
        if (!event) {
          continue;
        }

        timeout = INITIAL_RETRY_DELAY;
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

      if (xhr.status < 400) {
        processLines(true);
      }
      done = true;

      if (xhr.status >= 400) {
        const error = new ClueReplicationError(xhr.status, fullUrl, collection.name);
        if (xhr.status >= 500) {
          void reportHttpFailure(error);
          reconnect();
        } else if (xhr.status === 401) {
          if (await reportHttpFailure(error)) {
            const refreshedToken = getToken()?.trim();
            if (refreshedToken && refreshedToken !== token && !isClosed()) {
              connect(INITIAL_RETRY_DELAY, refreshedToken);
              emitResyncIfNeeded();
            }
          }
        } else {
          void reportHttpFailure(error);
        }
        return;
      }

      reconnect();
    };

    xhr.onload = () => void handleEnd();
    xhr.onerror = () => void handleEnd();
    xhr.onprogress = () => (xhr.status >= 400 ? void handleEnd() : processLines());

    xhr.send();
  };

  collection.onClose.push(() => {
    closed = true;
    if (retryTimer !== null) {
      clearTimeout(retryTimer);
      retryTimer = null;
    }
    currentXhr?.abort();
  });

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
