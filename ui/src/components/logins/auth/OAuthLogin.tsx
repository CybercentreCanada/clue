import { Button, CircularProgress, Stack } from '@mui/material';
import api from 'api';
import { useEffect, useState } from 'react';
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

  useEffect(() => {
    if (searchParams.get('code')) {
      setButtonLoading(true);
      doOAuth().finally(() => setButtonLoading(false));
    }
  }, [doOAuth, searchParams]);

  return (
    <Stack spacing={1}>
      {providers.map(item => (
        <Button
          fullWidth
          key={item}
          variant="contained"
          color="primary"
          disabled={buttonLoading}
          href={api.auth.login.uri(new URLSearchParams({ oauth_provider: item }))}
          startIcon={buttonLoading && <CircularProgress size={24} />}
        >
          {t('route.login.button.oauth.' + item.replace(/_/g, ' '))}
        </Button>
      ))}
    </Stack>
  );
};

export default OAuthLogin;
