import useLocalStorageItem from 'commons/components/utils/hooks/useLocalStorageItem';
import { createContext, ReactElement, useMemo } from 'react';
import { AppStorageKeys } from '../AppConstants';
import { AppQuickSearchContextType } from '../AppContexts';
import { AppSearchService } from '../AppSearchService';
import useAppConfigs from '../hooks/useAppConfigs';
import AppSearchServiceProvider from './AppSearchServiceProvider';

const { LS_KEY_SHOW_QUICK_SEARCH } = AppStorageKeys;

type AppQuickSearchProviderProps = {
  search?: AppSearchService;
  children: ReactElement | ReactElement[];
};

export const AppQuickSearchContext = createContext<AppQuickSearchContextType>(null);

export default function AppQuickSearchProvider({ search, children }: AppQuickSearchProviderProps) {
  const { preferences } = useAppConfigs();
  const [show, setShow] = useLocalStorageItem(LS_KEY_SHOW_QUICK_SEARCH, preferences.defaultShowQuickSearch);
  const context = useMemo(
    () => ({
      show: preferences.allowQuickSearch && show,
      setShow,
      toggle: () => setShow(!show)
    }),
    [preferences.allowQuickSearch, show, setShow]
  );
  return (
    <AppQuickSearchContext.Provider value={context}>
      <AppSearchServiceProvider service={search}>{children}</AppSearchServiceProvider>
    </AppQuickSearchContext.Provider>
  );
}
