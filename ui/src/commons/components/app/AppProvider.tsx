import { PaletteMode, StyledEngineProvider, ThemeProvider, useMediaQuery } from '@mui/material';
import { AppPreferenceConfigs, AppSiteMapConfigs, AppThemeConfigs } from 'commons/components/app/AppConfigs';
import useLocalStorageItem from 'commons/components/utils/hooks/useLocalStorageItem';
import i18n from 'i18n';
import { createContext, ReactNode, useCallback, useMemo } from 'react';
import useThemeBuilder from '../utils/hooks/useThemeBuilder';
import { AppStorageKeys } from './AppConstants';
import { AppContextType, AppNotificationService } from './AppContexts';
import { AppDefaultsPreferencesConfigs } from './AppDefaults';

import { AppSearchService } from './AppSearchService';
import { AppUser, AppUserService } from './AppUserService';
import AppBarProvider from './providers/AppBarProvider';
import AppLayoutProvider from './providers/AppLayoutProvider';
import AppLeftNavProvider from './providers/AppLeftNavProvider';
import AppSnackbarProvider from './providers/AppSnackbarProvider';
import AppUserProvider from './providers/AppUserProvider';

const { LS_KEY_DARK_MODE } = AppStorageKeys;

export type AppProviderProps<U extends AppUser> = {
  preferences?: AppPreferenceConfigs;
  theme?: AppThemeConfigs;
  sitemap?: AppSiteMapConfigs;
  user?: AppUserService<U>;
  search?: AppSearchService;
  notification?: AppNotificationService;
  children: ReactNode;
};

export const AppContext = createContext<AppContextType>(null);

export default function AppProvider<U extends AppUser>({
  theme,
  user,
  search,
  sitemap,
  notification,
  preferences,
  children
}: AppProviderProps<U>) {
  // Since we can't useAppConfig yet, we explicitly merge default and preferences config
  //  to help figure the default theme mode.
  const { allowThemeSelection, defaultTheme } = { ...AppDefaultsPreferencesConfigs, ...(preferences || {}) };

  // Store theme state in local storage.
  const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)');
  const [darkMode, setDarkMode] = useLocalStorageItem(LS_KEY_DARK_MODE, defaultTheme === 'dark' || prefersDarkMode);

  // Enforce default theme if selection isn't alloweed.
  const _darkMode = allowThemeSelection ? darkMode : defaultTheme === 'dark';

  // Create MUI Themes.
  const { lightTheme, darkTheme } = useThemeBuilder(theme);

  // Callback to toggle theme.
  const toggleTheme = useCallback(() => setDarkMode(!darkMode), [darkMode, setDarkMode]);

  // Callback to toggle language.
  const toggleLanguage = useCallback(() => i18n.changeLanguage(i18n.language === 'en' ? 'fr' : 'en'), []);

  // Memoize context value to prevent extraneous renders on components that use it.
  const contextValue = useMemo(() => {
    return {
      theme: (darkMode ? 'dark' : 'light') as PaletteMode,
      configs: { preferences, theme, sitemap },
      toggleTheme,
      toggleLanguage
    };
  }, [darkMode, preferences, theme, sitemap, toggleTheme, toggleLanguage]);

  return (
    <AppContext.Provider value={contextValue}>
      <StyledEngineProvider injectFirst>
        <ThemeProvider theme={_darkMode ? darkTheme : lightTheme}>
          <AppUserProvider service={user}>
            <AppBarProvider search={search} notification={notification}>
              <AppLeftNavProvider>
                <AppLayoutProvider>
                  <AppSnackbarProvider>{children}</AppSnackbarProvider>
                </AppLayoutProvider>
              </AppLeftNavProvider>
            </AppBarProvider>
          </AppUserProvider>
        </ThemeProvider>
      </StyledEngineProvider>
    </AppContext.Provider>
  );
}
