import type { StatusDocument } from 'lib/database/types';
import type { BulkEnrichResponses, EnrichResponses, FailedRequest, Selector } from 'lib/types/lookup';
import type { ClassificationDefinition } from 'lib/utils/classificationParser';

export interface ClueEnrichContextType {
  /**
   * What sources are available to query?
   */
  availableSources: string[];

  /**
   * The sources a user has selected to query data from. An empty array means all available sources will be used.
   */
  sources: string[];

  /**
   * Set the list of enrichments to enrich data with.
   * @param enrichments The list of enrichments
   */
  setSources: (enrichments: string[]) => void;

  /**
   * List of all failed enrichments
   */
  failedEnrichments?: FailedRequest[];

  /**
   * Bulk enrich a large number of values in a single request.
   * @param bulkData A list of bulk enrich requests, specifying the type and value
   * @param options Set some options about how the enrichment should be enriched
   * @returns a list of enrichment results broken down by type and value
   */
  bulkEnrich: (
    bulkData: Selector[],
    options?: {
      classification?: string;
      timeout?: number;
      force?: boolean;
      includeRaw?: boolean;
      noCache?: boolean;
      sources?: string[];
    }
  ) => Promise<BulkEnrichResponses>;

  /**
   * Enrich a single item
   * @param type The type of the data to enrich
   * @param value The value itself
   * @param options Set some options about how the enrichment should be enriched
   * @returns a list of enrichment results for the given type and value
   */
  enrich: (
    type: string,
    value: string,
    options?: {
      classification?: string;
      timeout?: number;
      force?: boolean;
      includeRaw?: boolean;
      noCache?: boolean;
      sources?: string[];
      append?: boolean;
    }
  ) => Promise<EnrichResponses>;

  /**
   * Enrich failed enrichments by source
   * @returns a list of enrichment results for all failed enrichments
   */
  enrichFailedEnrichments: () => Promise<void>;

  /**
   * Queue a value for asynchronous enrichment. Slightly slower, but massively more efficient for your network as it
   * uses bulkEnrich, while returning a single value.
   * @param type The type of the data to enrich
   * @param value The value itself
   * @param classification An optional indicator-specific classification
   * @returns a list of enrichment results for the given type and value
   */
  queueEnrich: (type: string, value: string, classification?: string) => Promise<StatusDocument>;

  /**
   * A set of regexes applications can use for detecting the clue type of a given string
   */
  typesDetection: { [type: string]: RegExp };

  /**
   * A helper function that automatically returns the clue type (or null if the type can't be inferred) of a given value
   * @param value The value whose type we should infer
   * @returns the inferred type
   */
  guessType: (value: string) => string | null;

  /**
   * Set the is ready state of the provider, when set to true, the provider will be able to issue http queries
   * @param value The value whose type we should infer
   * @returns the inferred type
   */
  setReady: (ready: boolean) => void;

  /**
   * Set the custom Iconify URL
   * @param value the URL to use for iconify
   */
  setCustomIconify: (value: string) => void;

  /**
   * Set the default classification given a classification definition
   * @param func the function the will return the default classification
   */
  setDefaultClassification: (func: (classification: ClassificationDefinition) => string) => void;

  /**
   * Is the clue context ready to enrich?
   */
  ready: boolean;

  defaultClassification: string;
}
