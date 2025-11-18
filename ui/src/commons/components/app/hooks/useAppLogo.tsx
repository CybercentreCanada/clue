import { useMemo } from 'react';
import useApp from './useApp';
import useAppConfigs from './useAppConfigs';

export default function useAppLogo() {
  const { theme } = useApp();
  const { preferences } = useAppConfigs();
  return useMemo(() => (theme === 'dark' ? preferences.appIconDark : preferences.appIconLight), [theme, preferences]);
}
