import type { WithLastUpdated } from 'lib/database/types';
import type { RxReplicationWriteToMasterRow, WithDeleted } from 'rxdb';

export type SyncResponse<T> = WithDeleted<WithLastUpdated<T>>[];

export interface Checkpoint {
  id: string;
  last_updated: number;
}

export type PushPayload<T> = RxReplicationWriteToMasterRow<T>[];
