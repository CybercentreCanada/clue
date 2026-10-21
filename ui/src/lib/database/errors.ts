/**
 * A safe description of an HTTP failure from the selector replication stream.
 *
 * The error intentionally contains request metadata only; authorization tokens and response bodies are never included.
 */
export class ClueReplicationError extends Error {
  readonly status: number;

  readonly url: string;

  readonly collection: string;

  constructor(status: number, url: string, collection: string) {
    super(`Replication stream for collection "${collection}" failed with HTTP status ${status}`);

    this.name = 'ClueReplicationError';
    this.status = status;
    this.url = url;
    this.collection = collection;
  }
}
