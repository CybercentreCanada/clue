import useLocalStorageItem from 'commons/components/utils/hooks/useLocalStorageItem';
import { useCallback, useMemo } from 'react';
import { v4 as uuid } from 'uuid';
import { TuiSearchFavouriteOption, TuiSearchFavouriteProvider } from '..';
import TuiSearchModel from '../models/TuiSearchModel';
import useTuiSearchParams from './useTuiSearchParams';

export default function useTuiSearchFavourites(localStorage: string): TuiSearchFavouriteProvider {
  const { serialize } = useTuiSearchParams();
  const [options, setOptions] = useLocalStorageItem<TuiSearchFavouriteOption[]>(localStorage, []);

  const onSave = useCallback(
    async (inputValue: string, model: TuiSearchModel) => {
      setOptions([
        ...options,
        {
          id: uuid(),
          name: inputValue,
          search: serialize(model.request()).toString()
        }
      ]);
      return true;
    },
    [options, setOptions, serialize]
  );

  const onDelete = useCallback(
    async (option: TuiSearchFavouriteOption) => {
      setOptions(options.filter(f => f !== option));
      return true;
    },
    [options, setOptions]
  );

  return useMemo(
    () => ({
      options,
      onSave,
      onDelete
    }),
    [options, onSave, onDelete]
  );
}
