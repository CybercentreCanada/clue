import { useContext } from 'react';
import { AppQuickSearchContext } from '../providers/AppQuickSearchProvider';

//
export default function useAppQuickSearch() {
  return useContext(AppQuickSearchContext);
}
