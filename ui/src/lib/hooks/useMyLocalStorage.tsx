import useLocalStorage from 'commons/components/utils/hooks/useLocalStorage';
import useLocalStorageItem from 'commons/components/utils/hooks/useLocalStorageItem';
import { LocalStorageContext } from 'components/app/providers/LocalStorageProvider';
import type { StorageKey } from 'lib/utils/constants';
import { MY_LOCAL_STORAGE_PREFIX } from 'lib/utils/constants';
import { useContext } from 'react';

const useMyLocalStorage = () => {
  return useLocalStorage(MY_LOCAL_STORAGE_PREFIX);
};

export const useMyLocalStorageItem = <T,>(key: StorageKey, initialValue?: T) => {
  return useLocalStorageItem(key, initialValue, MY_LOCAL_STORAGE_PREFIX);
};

export const useMyLocalStorageProvider = () => {
  return useContext(LocalStorageContext);
};

export default useMyLocalStorage;
