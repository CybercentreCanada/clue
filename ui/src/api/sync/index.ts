import { hget, hpost, joinAllUri, joinUri, uri as parentUri } from 'api';
import type { AxiosRequestConfig } from 'axios';
import type { Checkpoint, PushPayload, SyncResponse } from 'lib/database/sync';
import type { SelectorCollection, SelectorDocType, WithLastUpdated } from 'lib/database/types';
import { StorageKey } from 'lib/utils/constants';
import { isNil } from 'lodash-es';
import type { DocumentsWithCheckpoint, WithDeleted } from 'rxdb';
import { Subject } from 'rxjs';
import { getStored } from 'utils/localStorage';

const uri = () => {
  return joinUri(parentUri(), 'sync');
};

const get = <T>(
  collection: 'selector' | 'status',
  id: string | null,
  timestamp: number,
  config?: AxiosRequestConfig
): Promise<SyncResponse<T>> => {
  const params = new URLSearchParams();

  params.set('limit', '250');

  if (!isNil(timestamp)) {
    params.set('updated_at', timestamp.toString());
  }

  if (!isNil(id)) {
    params.set('id', id.toString());
  }

  return hget(joinAllUri(uri(), collection), params, config);
};

const post = <T>(
  collection: 'selector' | 'status',
  payload: PushPayload<T>,
  config?: AxiosRequestConfig
): Promise<WithDeleted<WithLastUpdated<T>>[]> => {
  return hpost(joinAllUri(uri(), collection), payload, config);
};

interface EventStreamEntry extends DocumentsWithCheckpoint<SelectorDocType, Checkpoint> {
  id: number;
}

const stream = (collection: SelectorCollection) => {
  const stream$ = new Subject<EventStreamEntry | 'RESYNC'>();
  const MAX_RETRY_DELAY = 60000; // Cap at 60 seconds

  let lastProcessedIndex = 0;
  const loggedEvents: number[] = [];

  const connect = (timeout = 1000) => {
    const _xhr = new XMLHttpRequest();

    const reconnect = () => {
      // eslint-disable-next-line no-console
      if (collection.closed) {
        return;
      }

      console.log(`Retrying live connection in ${timeout}ms...`);

      setTimeout(() => {
        // Exponential increase
        connect(Math.min(timeout * 2, MAX_RETRY_DELAY));
      }, timeout);
    };

    _xhr.open('GET', joinAllUri(uri(), collection.name, 'stream'), true);

    collection.onClose.push(() => {
      _xhr.abort();
    });

    const authToken = getStored(StorageKey.APP_TOKEN);
    _xhr.setRequestHeader('Accept', 'text/event-stream');
    _xhr.setRequestHeader('Authorization', `Bearer ${authToken}`);

    _xhr.onload = () => {
      // eslint-disable-next-line @typescript-eslint/no-use-before-define
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

export { get, post, stream, uri };
