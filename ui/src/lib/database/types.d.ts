import type { Annotation, Selector, WithExtra } from 'lib/types/lookup';
import type { RxCollection, RxDatabase, RxDocument } from 'rxdb';

export interface DatabaseConfig {
  storageType?: 'memory' | 'sessionStorage';
  testing?: boolean;
  devMode?: boolean;
}

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
