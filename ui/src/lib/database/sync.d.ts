import { SelectorDocType } from './types';

export interface SyncResponse {
  documents: SelectorDocType[];
  checkpoint: {
    id: string;
    lastUpdated: number;
  };
}

export type PushPayload<T> = RxReplicationWriteToMasterRow<T>[];
