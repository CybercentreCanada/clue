import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import TuiSearchItems, { TuiSearchItemsResult } from '../models/TuiSearchItems';
import TuiSearchModel from '../models/TuiSearchModel';

export default function useTuiSearchItems<T>(limit?: number) {
  const [searching, setSearching] = useState<boolean>(false);
  const searchItems = useRef<TuiSearchItems<T>>(new TuiSearchItems());
  const [result, setResult] = useState<{ model: TuiSearchModel; result: TuiSearchItemsResult<T> }>({
    model: TuiSearchModel.build({ limit }),
    result: {
      limit,
      offset: 0,
      total: 0,
      items: []
    }
  });

  useEffect(() => {
    setSearching(false);
  }, [result]);

  const load = useCallback((items: T[], model?: TuiSearchModel) => {
    searchItems.current.load(items);
    setResult(current => ({
      model: model || current.model,
      result: searchItems.current.apply(model || current.model).result()
    }));
  }, []);

  const apply = useCallback(
    (model?: TuiSearchModel) => {
      // Search progress start ...
      setSearching(true);

      // Make sure we retain specified limit.
      if (model && !model.hasLimit() && limit) {
        model.limit(limit);
      }

      // Apply filters, sorters and update state.
      setResult(current => ({
        model: model || current.model,
        result: searchItems.current.apply(model || current.model).result()
      }));
    },
    [limit]
  );

  const reset = useCallback(() => {
    searchItems.current.reset();
    setResult(current => ({ model: current.model.reset(), result: searchItems.current.reset().result() }));
  }, []);

  return useMemo(
    () => ({
      ...result,
      searching,
      load,
      apply,
      reset
    }),
    [result, searching, load, apply, reset]
  );
}
