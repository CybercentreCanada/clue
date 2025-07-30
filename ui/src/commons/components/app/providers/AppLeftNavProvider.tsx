import useAppConfigs from 'commons/components/app/hooks/useAppConfigs';
import useLocalStorageItem from 'commons/components/utils/hooks/useLocalStorageItem';
import { createContext, ReactNode, useCallback, useMemo, useState } from 'react';
import { AppLeftNavElement } from '../AppConfigs';
import { AppStorageKeys } from '../AppConstants';
import { AppLeftNavContextType } from '../AppContexts';

const { LS_KEY_LEFTNAV_OPEN } = AppStorageKeys;

type LeftNavProviderProps = {
  children: ReactNode;
};

export const AppLeftNavContext = createContext<AppLeftNavContextType>(null);

export default function AppLeftNavProvider({ children }: LeftNavProviderProps) {
  const { preferences } = useAppConfigs();
  const [open, setOpen] = useLocalStorageItem(LS_KEY_LEFTNAV_OPEN, preferences.defaultDrawerOpen);
  const [elements, setElements] = useState<AppLeftNavElement[]>();
  const toggle = useCallback(() => setOpen(!open), [open, setOpen]);
  const context = useMemo(
    () => ({
      open,
      elements: elements || preferences.leftnav.elements,
      setOpen,
      setElements,
      toggle
    }),
    [open, elements, preferences.leftnav.elements, setOpen, toggle]
  );
  return <AppLeftNavContext.Provider value={context}>{children}</AppLeftNavContext.Provider>;
}
