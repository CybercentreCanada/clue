import { useContext } from 'react';
import { TuiListItemsContext, TuiListItemsState } from '../TuiListProvider';

export default function useTuiListItems<T>() {
  return useContext(TuiListItemsContext) as TuiListItemsState<T>;
}
