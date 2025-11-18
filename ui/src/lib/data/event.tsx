import type { OptionsObject } from 'notistack';
import type { ReactNode } from 'react';

export const SNACKBAR_EVENT_ID = 'snackbar.message';
export const SHOW_EVENT_ID = 'clue.showPopup';
export const HIDE_EVENT_ID = 'clue.hidePopup';

export type SnackbarEvents = {
  message: ReactNode;
  level: 'success' | 'error' | 'info' | 'warning';
  timeout?: number;
  options?: OptionsObject;
};
