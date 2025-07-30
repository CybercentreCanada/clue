import type { NestedDataset } from './graph';

export interface FetcherDefinition {
  id: string;
  classification: string;
  description: string;
  format: string;
  supported_types: string[];
}

interface BaseFetcherResult {
  outcome: 'success' | 'failure';
  error: string;
  link: string;
  format: string;
}

export interface FetcherImageResult extends BaseFetcherResult {
  data: {
    image: string;
    alt: string;
  };
  format: 'image';
}

export interface FetcherJsonResult extends BaseFetcherResult {
  data: any;
  format: 'json';
}

export interface FetcherMarkdownResult extends BaseFetcherResult {
  data: string;
  format: 'markdown';
}

export interface FetcherGraphResult extends BaseFetcherResult {
  data: NestedDataset;
  format: 'graph';
}

export interface FetcherStatusResult extends BaseFetcherResult {
  data: {
    empty: boolean;
    labels: { language: string; label: string }[];
    link?: string;
    icon?: string;
    color?: string;
  };
  format: 'status';
}

export type FetcherResult =
  | FetcherImageResult
  | FetcherJsonResult
  | FetcherGraphResult
  | FetcherMarkdownResult
  | FetcherStatusResult;

export type FetcherDefinitionsResponse = { [type: string]: FetcherDefinition };
