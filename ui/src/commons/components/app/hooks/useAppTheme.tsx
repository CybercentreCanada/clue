import { PaletteMode } from '@mui/material';
import { useMemo } from 'react';
import useApp from './useApp';

export type AppThemeType = {
  theme: PaletteMode;
  isDark: boolean;
  isLight: boolean;
  toggle: () => void;
};

export default function useAppTheme(): AppThemeType {
  const { theme, toggleTheme } = useApp();
  return useMemo(
    () => ({
      theme,
      isDark: theme === 'dark',
      isLight: theme === 'light',
      toggle: toggleTheme
    }),
    [theme, toggleTheme]
  );
}
