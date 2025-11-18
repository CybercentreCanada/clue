import { useContext } from 'react';
import { AppSearchServiceContextType } from '../AppContexts';
import { AppSearchServiceContext } from '../providers/AppSearchServiceProvider';

export default function useAppSearchService<T = any>(): AppSearchServiceContextType<T> {
  return useContext(AppSearchServiceContext);
}
