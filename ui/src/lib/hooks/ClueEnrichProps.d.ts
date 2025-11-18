import type { AxiosRequestConfig } from 'axios';
import type { Selector } from 'lib/types/lookup';

export interface ClueEnrichProps {
  /**
   * The base URL that refers to the clue API. leaving this empty will forward requests to the current origin.
   */
  baseURL?: string;

  /**
   * How many IOCs should be sent in each network request? Defaults to 20.
   */
  chunkSize?: number;

  /**
   * How many requests should clue dispatch at once?
   */
  maxRequestCount?: number;

  /**
   * What should the default timeout be, if no timeout is supplied in an enrichment call?
   */
  defaultTimeout?: number;

  /**
   * Should enrichment be enabled? If set to false, enrichment will only be used when explicitly called.
   */
  enabled?: boolean;

  /**
   * What should the default classification be for indicators?
   */
  classification?: string;

  /**
   * Is the clue provider ready to do queries?
   */
  ready?: boolean;

  /**
   * Get an access token for the clue API.
   *
   * @returns An access token valid for use with the clue API.
   */
  getToken?: () => string;

  /**
   * Should we use custom deployment or public deployment of Iconify
   */
  publicIconify?: boolean;

  /**
   * Add modify the Axios request configuration before the request is sent
   * @param config The existing axios request config
   */
  onNetworkCall?: (config: AxiosRequestConfig) => AxiosRequestConfig;

  /**
   * Modify the list of sources enrichments are requested from before the
   * @param configuredSources The list of sources configured globally to execute
   * @param availableSources The full list of available sources in clue
   * @param selectors The list of selectors about to be enriched
   */
  pickSources?: (configuredSources: string[], availableSources: string[], selectors: Selector[]) => string[] | null;

  /**
   * Should we skip making the clue config call? Only set this if you'll manually make the call. Likely only for internal use.
   */
  skipConfigCall?: boolean;

  /**
   * A hostname for the custom Iconify domain to use. Only used if publicIconify is set to false.
   */
  customIconify?: string;

  /**
   * Flag for enabled/disabling Debug logging. Default is true.
   */
  debugLogging?: boolean;
}
