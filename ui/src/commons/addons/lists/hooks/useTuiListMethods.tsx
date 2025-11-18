import { useContext } from 'react';
import { TuiListMethodContext, TuiListMethodsState } from '../TuiListProvider';

export default function useTuiListMethods<T>() {
  return useContext(TuiListMethodContext) as TuiListMethodsState<T>;
}
