import { v4 as uuid } from 'uuid';

import useLocalStorageItem from 'commons/components/utils/hooks/useLocalStorageItem';
import { useCallback, useMemo } from 'react';
import { TuiQueryItem, TuiQueryStoreService } from '..';

export const useLocalQueryStore = <T extends TuiQueryItem>(storageKey: string): TuiQueryStoreService<T> => {
  const [items, setItems] = useLocalStorageItem<T[]>(storageKey, []);

  const onCreate = useCallback(
    async (name: string, value: string) => {
      const newId = uuid();

      setItems([
        ...items,
        {
          id: newId,
          type: 'query',
          name,
          value
        } as T
      ]);

      return newId;
    },
    [items, setItems]
  );

  const onSave = useCallback(
    async (item: T) => {
      if (items.some(i => i.id === item.id)) {
        setItems(items.map(i => (i.id === item.id ? item : i)));
      } else {
        if (!item.id) {
          item.id = uuid();
        }
        setItems([...items, item]);
      }

      return item.id;
    },
    [items, setItems]
  );

  const onDelete = useCallback(
    async (id: string) => {
      setItems(items.filter(i => i.id !== id));
      return true;
    },
    [items, setItems]
  );

  return useMemo(
    () => ({
      ready: true,
      items,
      onCreate,
      onSave,
      onDelete
    }),
    [items, onCreate, onSave, onDelete]
  );
};
