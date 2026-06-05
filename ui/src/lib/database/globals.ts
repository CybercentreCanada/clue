import type { RxReplicationState } from 'rxdb/plugins/replication';

export const REPLICATORS: { [timestamp: string]: RxReplicationState<any, any> } = {};
