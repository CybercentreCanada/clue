import { createContext, ReactElement, useMemo, useState } from 'react';
import { AppNotificationService, AppNotificationServiceContextType, AppNotificationServiceState } from '../AppContexts';

const DEFAULT_CONTEXT: AppNotificationServiceContextType = {
  provided: false,
  service: {
    feedUrls: [],
    notificationRenderer: null
  },
  state: { urls: [], set: () => null }
};

export const AppNotificationServiceContext = createContext<AppNotificationServiceContextType>(DEFAULT_CONTEXT);

export default function AppNotificationServiceProvider({
  service,
  children
}: {
  service?: AppNotificationService;
  children: ReactElement | ReactElement[];
}) {
  // Default implementation of the AppNotificationService using configuration preferences.
  const defaultService: AppNotificationService = useMemo(() => {
    return {
      feedUrls: null,
      notificationRenderer: null
    };
  }, []);

  const [state, setState] = useState<AppNotificationServiceState>(DEFAULT_CONTEXT.state);

  // Memoize context value to prevent unnecessary renders.0
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

  return <AppNotificationServiceContext.Provider value={context}>{children}</AppNotificationServiceContext.Provider>;
}
