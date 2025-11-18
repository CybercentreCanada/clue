import { createContext, ReactElement, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { AppSearchServiceContextType, AppSearchServiceState } from '../AppContexts';
import { AppSearchService } from '../AppSearchService';
import useAppConfigs from '../hooks/useAppConfigs';

const DEFAULT_CONTEXT: AppSearchServiceContextType = {
  provided: false,
  service: {
    itemRenderer: (item: any) => <div />
  },
  state: {
    searching: false,
    menu: false,
    mode: 'inline',
    items: null,
    set: () => null
  }
};

export const AppSearchServiceContext = createContext<AppSearchServiceContextType>(DEFAULT_CONTEXT);

export default function AppSearchServiceProvider<T = any>({
  service,
  children
}: {
  service?: AppSearchService<T>;
  children: ReactElement | ReactElement[];
}) {
  // Hooks required for default implementation.
  const navigate = useNavigate();
  const { preferences } = useAppConfigs();

  // Default implementation of the AppSearchService using configuration preferences.
  const defaultService: AppSearchService<any> = useMemo(() => {
    const searchUri = preferences.topnav.quickSearchURI;
    const params = preferences.topnav.quickSearchParam;
    return {
      onEnter: (value: string) => {
        navigate(`${searchUri}?${params}=${encodeURIComponent(value)}`);
      },
      itemRenderer: (item: any) => <div />
    };
  }, [preferences, navigate]);

  // The state of the search service.
  const [state, setState] = useState<AppSearchServiceState<T>>(DEFAULT_CONTEXT.state);

  // Memoize context value to prevent unnecessary renders.
  const context = useMemo(
    () => ({
      provided: !!service,
      service: service || defaultService,
      state: {
        ...state,
        set: setState
      }
    }),
    [service, defaultService, state]
  );

  return <AppSearchServiceContext.Provider value={context}>{children}</AppSearchServiceContext.Provider>;
}
