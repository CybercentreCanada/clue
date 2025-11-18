import type { PopoverProps } from '@mui/material';

interface EnrichmentProps {
  /**
   * The type of the selector to enrich.
   */
  type?: string;

  /**
   * The selector to enrich.
   */
  value: string;

  /**
   * The classification of the selector.
   */
  classification?: string;

  /**
   * Should the component show the extra context icon?
   */
  contextIcon?: boolean;

  /**
   * Should the component show counters?
   */
  counters?: boolean;

  /**
   * Disable the onclick functionality, and don't automatically show the related popup
   */
  hideDetails?: boolean;

  /**
   * Show the preview for extra icons on mouseover?
   */
  showPreview?: boolean;

  /**
   * Should the component hide the loading icon?
   */
  hideLoading?: boolean;

  /**
   * Force the element to show the details popup.
   */
  forceDetails?: boolean;

  /**
   * Callback for when the popup wants to close
   */
  setForceDetails?: (value: boolean) => void;

  /**
   * Should the component show a details icon to open the popup instead of simply clicking the selector?
   */
  useDetailsIcon?: boolean;

  /**
   * Skip enriching the value, thereby only showing cached results?
   */
  skipEnrichment?: boolean;

  /**
   * Props for various subcomponents of the enrichment component.
   */
  slotProps?: {
    popover?: Omit<PopoverProps, 'open'>;
  };
}

export default EnrichmentProps;
