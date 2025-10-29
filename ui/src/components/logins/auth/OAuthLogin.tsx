import { Button, CircularProgress, Stack } from '@mui/material';
import api from 'api';
import { useMyLocalStorageItem } from 'lib/hooks/useMyLocalStorage';
import { StorageKey } from 'lib/utils/constants';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import useLogin from '../hooks/useLogin';

type OAuthLoginProps = {
  providers: string[];
};

const OAuthLogin = ({ providers }: OAuthLoginProps) => {
  const [searchParams] = useSearchParams();
  const { t } = useTranslation();
  const { doOAuth } = useLogin();
  const [buttonLoading, setButtonLoading] = useState(false);

  const setNonce = useMyLocalStorageItem(StorageKey.LOGIN_NONCE)[1];

  useEffect(() => {
    if (searchParams.get('code')) {
      setButtonLoading(true);
      doOAuth().finally(() => setButtonLoading(false));
    }
  }, [doOAuth, searchParams]);

  const nonce = useMemo(() => {
    // Generate a cryptographically secure random 16-byte nonce, hex-encoded
    const array = new Uint8Array(16);
    window.crypto.getRandomValues(array);
    return Array.from(array, b => b.toString(16).padStart(2, '0')).join('');
  }, []);

  return (
    <Stack spacing={1}>
      {providers.map(item => (
        <Button
          fullWidth
          key={item}
          variant="contained"
          color="primary"
          disabled={buttonLoading}
          href={api.auth.login.uri(new URLSearchParams({ oauth_provider: item, nonce }))}
          onClick={() => setNonce(nonce)}
          startIcon={buttonLoading && <CircularProgress size={24} />}
        >
          {t('route.login.button.oauth.' + item.replace(/_/g, ' '))}
        </Button>
      ))}
    </Stack>
  );
};

export default OAuthLogin;
