import type { Annotation, Selector, WithExtra } from 'lib/types/lookup';
import type { RxCollection, RxDatabase, RxDocument } from 'rxdb';

/**
 * Configuration options for the database.
 */
export interface DatabaseConfig {
  /**
   * The type of storage mechanism to use for persisting database data.
   * - `'memory'`: Store data in memory (lost on page refresh)
   * - `'sessionStorage'`: Store data in browser's sessionStorage (persists during session)
   *
   * @default 'memory'
   */
  storageType?: 'memory' | 'sessionStorage';

  /**
   * Indicates whether the database is running in testing mode.
   * When enabled, may apply test-specific configurations or disable certain features.
   *
   * @default false
   */
  testing?: boolean;

  /**
   * Indicates whether the database is running in development mode.
   * When enabled, provides additional logging and debugging capabilities.
   *
   * @default false
   */
  devMode?: boolean;

  /**
   * Enables data replication to a remote server.
   * When enabled, database changes are synchronized with the remote storage.
   *
   * @default false
   */
  replicate?: boolean;

  /**
   * The base URL of the clue API server used for replication and remote operations.
   *
   * @example 'https://api.clue.example.com'
   */
  baseURL?: string;

  /**
   * Add modify the Axios request configuration before the request is sent
   *
   * @param config The existing axios request config
   */
  onNetworkCall?: (config: AxiosRequestConfig) => AxiosRequestConfig;

  /**
   * Get an access token for the clue API. Used during replication.
   *
   * @returns An access token valid for use with the clue API.
   */
  getToken?: () => string;
}

export type WithLastUpdated<T> = T & {
  updated_at: number;
};

export interface SelectorDocType {
  id: string;
  source: string;
  type: string;
  value: string;
  classification: string;
  count: number;
  link?: string;
  raw_data?: string;
  error?: string;
  maintainer?: string;
  datahub_link?: string;
  documentation_link?: string;
  latency: number;
  annotations: Annotation[];
}

export type SelectorDocMethods = {
  getAnnotations: () => WithExtra<Annotation>[];
};

export interface SelectorCollectionMethods {}

export type SelectorDocument = RxDocument<SelectorDocType, SelectorDocMethods>;

export type SelectorCollection = RxCollection<SelectorDocType, SelectorDocMethods, SelectorCollectionMethods>;

export interface StatusDocType {
  id: string;
  type: string;
  value: string;
  classification: string;
  status: 'pending' | 'in-progress' | 'complete';
  sources?: string[];
}

export type StatusDocMethods = {
  toSelector: () => Selector;
};

export type StatusCollectionMethods = {
  queueInsert: (value: StatusDocType) => Promise<StatusDocument>;
};

export type StatusDocument = RxDocument<StatusDocType, StatusDocMethods>;

export type StatusCollection = RxCollection<StatusDocType, StatusDocMethods, StatusCollectionMethods>;

export type ClueDatabaseCollections = {
  selectors: SelectorCollection;
  status: StatusCollection;
};

export type ClueDatabase = RxDatabase<ClueDatabaseCollections>;
