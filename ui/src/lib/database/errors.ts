/**
 * HTTP failure metadata only: never include credentials or response bodies.
 */
export class ClueReplicationError extends Error {
  constructor(
    readonly status: number,
    readonly url: string,
    readonly collection: string
  ) {
    super(`Replication stream for collection "${collection}" failed with HTTP status ${status}`);
    this.name = 'ClueReplicationError';
  }
}
