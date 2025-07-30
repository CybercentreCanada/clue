import { createContext, ReactNode, useMemo, useState } from 'react';
import { AppSwitcherItem } from '../AppConfigs';
import { AppSwitcherContextType } from '../AppContexts';
import useAppConfigs from '../hooks/useAppConfigs';

type AppSwitcherProviderProps = {
  children: ReactNode;
};

export const AppSwitcherContext = createContext<AppSwitcherContextType>(null);

export default function AppSwitcherProvider({ children }: AppSwitcherProviderProps) {
  const { preferences } = useAppConfigs();
  const [items, setItems] = useState<AppSwitcherItem[]>(preferences.topnav.apps || []);
  const context = useMemo(() => ({ items, empty: !items || items.length === 0, setItems }), [items]);
  return <AppSwitcherContext.Provider value={context}>{children}</AppSwitcherContext.Provider>;
}
