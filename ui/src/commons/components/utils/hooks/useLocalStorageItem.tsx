import { MY_LOCAL_STORAGE_PREFIX } from 'lib/utils/constants';
import { isNil } from 'lodash-es';
import { useEffect, useMemo, useState } from 'react';
import useLocalStorage from './useLocalStorage';

/**
 * This hooks backs the typical 'useState' hook with local storage.
 *
 * This means that it will initialize with the value stored in local storage.
 *
 * State changes are also persisted to local storage.
 *
 * All this ensures the state is preserved across inializations.
 *
 * @param key - local storage key under which to store the state.
 * @param initialValue - local storage initialization value.
 * @param prefix - prefix for the local storage key.
 * @returns a stateful value, a function to update it, and a function to remove it.
 */
export default function useLocalStorageItem<T>(
  key: string,
  initialValue?: T,
  prefix?: string
): [T, (value: T, save?: boolean) => void, () => void] {
  const { get, set, has, remove } = useLocalStorage(prefix ?? MY_LOCAL_STORAGE_PREFIX);
  const [value, setValue] = useState<T>(get(key) ?? initialValue);

  useEffect(() => {
    if (initialValue !== null && initialValue !== undefined && !has(key)) {
      set(key, initialValue);
    }
  }, [key, initialValue, has, set]);

  return useMemo(
    () => [
      value,
      (newValue, save = true) => {
        if (save) {
          if (!isNil(newValue)) {
            set(key, newValue);
          } else {
            remove(key);
          }
        }

        setValue(newValue);
      },
      () => remove(key)
    ],
    [key, value, set, remove]
  );
}
