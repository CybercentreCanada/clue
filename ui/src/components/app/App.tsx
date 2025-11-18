import api from 'api';
import type { AppPreferenceConfigs, AppSiteMapConfigs, AppThemeConfigs } from 'commons/components/app/AppConfigs';
import AppProvider from 'commons/components/app/AppProvider';
import LayoutSkeleton from 'commons/components/app/AppSkeleton';
import type { AppUserService } from 'commons/components/app/AppUserService';
import useAppLayout from 'commons/components/app/hooks/useAppLayout';
import useAppSwitcher from 'commons/components/app/hooks/useAppSwitcher';
import useAppUser from 'commons/components/app/hooks/useAppUser';
import Modal from 'components/elements/display/Modal';
import useMyApi from 'components/hooks/useMyApi';
import useMyPreferences from 'components/hooks/useMyPreferences';
import useMySitemap from 'components/hooks/useMySitemap';
import useMySnackbar from 'components/hooks/useMySnackbar';
import useMyTheme from 'components/hooks/useMyTheme';
import useMyUser from 'components/hooks/useMyUser';
import LoginScreen from 'components/logins/Login';
import useLogin from 'components/logins/hooks/useLogin';
import NotFoundPage from 'components/routes/404';
import Contributing from 'components/routes/Contributing';
import Documentation from 'components/routes/Documentation';
import Fetchers from 'components/routes/Fetchers';
import Logout from 'components/routes/Logout';
import PluginDashboard from 'components/routes/PluginDashboard';
import Examples from 'components/routes/examples';
import Home from 'components/routes/home';
import Settings from 'components/routes/settings/Settings';
import type { SnackbarEvents } from 'lib/data/event';
import { SNACKBAR_EVENT_ID } from 'lib/data/event';
import { ClueActionProvider } from 'lib/hooks/ClueActionContext';
import { ClueComponentProvider } from 'lib/hooks/ClueComponentContext';
import { ClueConfigProvider } from 'lib/hooks/ClueConfigProvider';
import { ClueDatabaseProvider } from 'lib/hooks/ClueDatabaseContext';
import { ClueEnrichProvider } from 'lib/hooks/ClueEnrichContext';
import { ClueFetcherProvider } from 'lib/hooks/ClueFetcherContext';
import { CluePopupProvider } from 'lib/hooks/CluePopupContext';
import { useClueEnrichSelector } from 'lib/hooks/selectors';
import useClueConfig from 'lib/hooks/useClueConfig';
import useMyLocalStorage from 'lib/hooks/useMyLocalStorage';
import { StorageKey } from 'lib/utils/constants';
import { safeAddEventListener } from 'lib/utils/window';
import type { ClueUser } from 'models/entities/ClueUser';
import type { FC, PropsWithChildren } from 'react';
import { useEffect } from 'react';
import { Routes, useLocation, useNavigate } from 'react-router';
import { BrowserRouter, Route } from 'react-router-dom';
import AppContainer from './AppContainer';
import LocalStorageProvider from './providers/LocalStorageProvider';
import ModalProvider from './providers/ModalProvider';

// Your application's initialization flow.
const MyApp: FC = () => {
  // From this point on, we use the commons' hook.
  const { getUser } = useLogin();
  const { dispatchApi } = useMyApi();
  const appLayout = useAppLayout();
  const appUser = useAppUser<ClueUser>();
  const location = useLocation();
  const navigate = useNavigate();
  const clueConfig = useClueConfig();
  const { setItems } = useAppSwitcher();
  const { get, set } = useMyLocalStorage();
  const clueSetReady = useClueEnrichSelector(state => state.setReady);
  const { showSuccessMessage, showErrorMessage, showInfoMessage, showWarningMessage } = useMySnackbar();

  useEffect(() => {
    const handleMessage = (event: CustomEvent<SnackbarEvents>) => {
      const { detail } = event;
      if (detail.level === 'success') {
        showSuccessMessage(detail.message, detail.timeout, detail.options);
      } else if (detail.level === 'error') {
        showErrorMessage(detail.message, detail.timeout, detail.options);
      } else if (detail.level === 'info') {
        showInfoMessage(detail.message, detail.timeout, detail.options);
      } else if (detail.level === 'warning') {
        showWarningMessage(detail.message, detail.timeout, detail.options);
      }
    };

    return safeAddEventListener(SNACKBAR_EVENT_ID, handleMessage);
  }, [showErrorMessage, showInfoMessage, showSuccessMessage, showWarningMessage]);

  // Simulate app loading time...
  // e.g. fetching initial app data, etc.
  useEffect(() => {
    dispatchApi(api.configs.get()).then(data => {
      clueConfig.setConfig(data);

      if (data?.configuration?.ui?.apps) {
        setItems(data.configuration.ui.apps);
      }
    });
    if (appUser.isReady() || (!get(StorageKey.APP_TOKEN) && !get(StorageKey.REFRESH_TOKEN))) {
      return;
    }

    getUser();
    // eslint-disable-next-line
  }, []);

  useEffect(() => {
    if (appUser.isReady()) {
      appLayout.setReady(true);
      clueSetReady(true);
    } else if (!get(StorageKey.APP_TOKEN) && !get(StorageKey.REFRESH_TOKEN)) {
      if (location.pathname !== '/login') {
        set(StorageKey.NEXT_LOCATION, location.pathname);
        set(StorageKey.NEXT_SEARCH, location.search);
        navigate('/login');
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appUser.isReady()]);

  // Register the routes
  return (
    <Routes>
      <Route path="/login" element={<LoginScreen />} />
      <Route path="/logout" element={<Logout />} />
      <Route
        path="/"
        element={
          appUser.isReady() && appLayout.ready && clueConfig.config.c12nDef ? <AppContainer /> : <LayoutSkeleton />
        }
      >
        <Route index element={<Home />} />
        <Route path="examples" element={<Examples />} />
        <Route path="fetchers" element={<Fetchers />} />
        <Route path="settings" element={<Settings />} />
        <Route path="help" element={<PluginDashboard />} />
        <Route path="help/contributing" element={<Contributing />} />
        <Route path="help/:pluginId" element={<Documentation />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
};

const MyAppProvider: FC<PropsWithChildren> = ({ children }) => {
  const myPreferences: AppPreferenceConfigs = useMyPreferences();
  const myTheme: AppThemeConfigs = useMyTheme();
  const mySitemap: AppSiteMapConfigs = useMySitemap();
  const myUser: AppUserService<ClueUser> = useMyUser();
  return (
    <ClueConfigProvider>
      <ClueComponentProvider>
        <AppProvider preferences={myPreferences} theme={myTheme} sitemap={mySitemap} user={myUser}>
          <ModalProvider>
            <LocalStorageProvider>
              <ClueDatabaseProvider>
                <ClueEnrichProvider publicIconify={false} skipConfigCall>
                  <ClueFetcherProvider>
                    <ClueActionProvider>
                      <CluePopupProvider>{children}</CluePopupProvider>
                    </ClueActionProvider>
                  </ClueFetcherProvider>
                </ClueEnrichProvider>
              </ClueDatabaseProvider>
            </LocalStorageProvider>
          </ModalProvider>
        </AppProvider>
      </ClueComponentProvider>
    </ClueConfigProvider>
  );
};

const App: FC = () => {
  return (
    <BrowserRouter>
      <MyAppProvider>
        <MyApp />
        <Modal />
      </MyAppProvider>
    </BrowserRouter>
  );
};

export default App;
