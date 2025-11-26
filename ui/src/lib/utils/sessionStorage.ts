import { MY_SESSION_STORAGE_PREFIX, StorageKey } from 'lib/utils/constants';
import debounce from 'lodash-es/debounce';

export const buildName = (name: string) => `${MY_SESSION_STORAGE_PREFIX}.${name}`;

const {
  _getStored: getStored,
  _removeStored: removeStored,
  _setStored: setStored
} = (() => {
  // In order to tamp down on the number of writes to session storage, we use a throttler to debounce writes.
  // This allows us to write to the same key many times in quick succession without actually writing it to session storage right away.
  let changes = {};

  const _getStored = <T = string>(name: StorageKey): T => {
    return (changes[buildName(name)] ?? JSON.parse(sessionStorage.getItem(buildName(name)))) as T;
  };

  const _removeStored = (name: StorageKey) => {
    delete changes[buildName(name)];
    sessionStorage.removeItem(buildName(name));
  };

  const _setStored = (name: StorageKey, item: any) => {
    changes[buildName(name)] = item;

    debounce(
      () => {
        Object.entries(changes).forEach(([_name, data]) => {
          try {
            sessionStorage.setItem(_name, JSON.stringify(data));
          } catch (e) {
            // eslint-disable-next-line no-console
            console.warn('Quota Error when saving to sessionStorage', e);
          }
        });

        changes = {};
      },
      250,
      { leading: false, trailing: true, maxWait: 800 }
    );
  };

  return { _getStored, _removeStored, _setStored };
})();

export { getStored, removeStored, setStored };

export const getAxiosCache = (): { [index: string]: any } => {
  return getStored(StorageKey.AXIOS_CACHE) ?? {};
};

export const setAxiosCache = (etag: string, value: any) => {
  const cache = getAxiosCache();
  cache[etag] = value;
  setStored(StorageKey.AXIOS_CACHE, cache);
};
