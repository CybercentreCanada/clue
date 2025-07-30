export interface Selector {
  type: string;
  value: string;
  classification?: string;
}

export interface FailedRequest extends BulkEnrichRequest {
  source: string;
}

export type BulkEnrichRequest = Selector;

export type WithExtra<T> = { latency: number; classification: string } & T;

export interface Annotation {
  analytic?: string;
  analytic_icon?: string;
  author?: string;
  confidence: number;
  icon?: string;
  link?: string;
  priority?: number;
  reliability?: number;
  timestamp?: string;
  type: 'opinion' | 'frequency' | 'owner' | 'assessment' | 'context' | 'activity' | 'mitigation';
  value: string | number;
  version?: string;
  summary: string;
  details?: string;
  quantity: number;
  ubiquitous: boolean;
}

export interface Enrichment {
  annotations: Annotation[];
  classification: string;
  count: number;
  link?: string;
  raw_data?: any;
}

export type EnrichResponse = {
  error?: string;
  items: Enrichment[];
  maintainer?: string;
  datahub_link?: string;
  documentation_link?: string;
  latency: number;
  source: string;
  type: string;
  value: string;
};

export type EnrichResponses = {
  [provider: string]: EnrichResponse;
};

export type BulkEnrichResponses = { [type: string]: { [value: string]: EnrichResponses } };

export type TypesDetectionResponse = { [type: string]: string };

export type TypesResponse = { [type: string]: string[] };
