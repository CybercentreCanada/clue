export const CLUE_API = import.meta.env.VITE_API;
export const LOCAL = CLUE_API === 'MOCK';
export const VERSION = import.meta.env.VITE_VERSION;

// A constant that will be used as prefix of all local storage keys.
export const MY_LOCAL_STORAGE_PREFIX = 'clue.ui';
export const MY_SESSION_STORAGE_PREFIX = `${MY_LOCAL_STORAGE_PREFIX}.cache`;

export enum StorageKey {
  PROVIDER = 'provider',
  REFRESH_TOKEN = 'refresh_token',
  APP_TOKEN = 'app_token',
  NEXT_LOCATION = 'next.location',
  NEXT_SEARCH = 'next.search',
  AXIOS_CACHE = 'axios.cache',
  COMPACT_JSON = 'compact_json_view',
  FLATTEN_JSON = 'flatten_json_view',
  PAGE_COUNT = 'page_count',
  CLUE_CACHE = 'results',
  LOGIN_NONCE = 'login_nonce',

  COLOR_SCHEME = 'color.scheme',
  SHOW_DIRECTIONALITY = 'show.directionality',
  SHOW_CARDS = 'show.cards',
  CARD_CUTOFF = 'card.cutoff',
  SHOW_MOUSE_POS = 'show.mouse.position',
  SHOW_COORDINATES = 'show.coordinates',
  PANEL_LOCATION = 'panel.location',
  FORCE_COLOR_SETTING = 'force.color.setting'
}

export const BUNDLE_SEPARATOR = '-X-';
