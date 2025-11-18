import api from 'api';
import type { LoginResponse, PostLoginBody } from 'api/auth/login';
import useAppUser from 'commons/components/app/hooks/useAppUser';
import LoginErrorModal from 'components/elements/display/modals/LoginErrorModal';
import useMyApi from 'components/hooks/useMyApi';
import useMyModal from 'components/hooks/useMyModal';
import useMySnackbar from 'components/hooks/useMySnackbar';
import useMyLocalStorage from 'lib/hooks/useMyLocalStorage';
import { StorageKey } from 'lib/utils/constants';
import type { ClueUser } from 'models/entities/ClueUser';
import { useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router';
import { useSearchParams } from 'react-router-dom';
import { saveLoginCredential } from 'utils/localStorage';

const useLogin = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { dispatchApi } = useMyApi();
  const { setUser } = useAppUser<ClueUser>();
  const { showErrorMessage } = useMySnackbar();
  const { t } = useTranslation();
  const { showModal } = useMyModal();
  const { get, remove } = useMyLocalStorage();

  // Get user information
  const getUser = useCallback(
    (userCredential?: LoginResponse) => {
      let user = userCredential?.user;
      if (!user) {
        const token = get<string>(StorageKey.APP_TOKEN);
        // Can we parse the JWT stored locally?
        if (token.includes('.')) {
          const rawJWT: { [index: string]: any } = JSON.parse(atob(token.split('.')[1]));
          user = rawJWT as ClueUser;
        }
      }

      try {
        user = Object.fromEntries(
          Object.entries(user).filter(([key, __]) => ['groups', 'name', 'preferred_username'].includes(key))
        ) as ClueUser;

        if (user) {
          setUser(user);

          // Either navigate to the original URL, or just the home page
          if (get(StorageKey.NEXT_LOCATION)) {
            navigate(get<string>(StorageKey.NEXT_LOCATION) + (get<string>(StorageKey.NEXT_SEARCH) ?? ''));
            remove(StorageKey.NEXT_LOCATION);
            remove(StorageKey.NEXT_SEARCH);
          } else if (location.pathname === '/login') {
            navigate('/');
          }
          // If the user is null but there's no exception?
        } else {
          setUser(null);
          showErrorMessage(t('user.error.failed'));
        }
      } catch (e) {
        // There's some sort of error with the getting of the user - log them out or throw an error
        if (e instanceof Error) {
          showModal(<LoginErrorModal error={e} />, {
            disableClose: true
          });
        }
      }
    },
    [setUser, get, location.pathname, navigate, remove, showErrorMessage, t, showModal]
  );

  // Generic login flow.
  const doLogin = useCallback(
    async (loginData: PostLoginBody) => {
      // Provide the login data to the API for the server to authenticate
      const userCredential = await dispatchApi(api.auth.login.post(loginData));

      if (!userCredential) {
        showErrorMessage(t('user.login.failed'));
      } else if (saveLoginCredential(userCredential)) {
        getUser(userCredential);
      }
    },
    [dispatchApi, getUser, showErrorMessage, t]
  );

  // OAuth login flow.
  const doOAuth = useCallback(async () => {
    const userCredential = await dispatchApi(api.auth.login.get(searchParams));
    if (saveLoginCredential(userCredential)) {
      getUser(userCredential);
    }
  }, [dispatchApi, searchParams, getUser]);

  // login service.
  return useMemo(
    () => ({
      doLogin,
      doOAuth,
      getUser
    }),
    [doLogin, doOAuth, getUser]
  );
};

export default useLogin;
