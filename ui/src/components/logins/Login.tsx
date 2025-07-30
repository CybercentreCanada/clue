import { Box, CircularProgress, useTheme } from '@mui/material';
import useAppBanner from 'commons/components/app/hooks/useAppBanner';
import PageCardCentered from 'commons/components/pages/PageCardCentered';
import useClueConfig from 'lib/hooks/useClueConfig';
import OAuthLogin from './auth/OAuthLogin';

const LoginScreen = () => {
  const theme = useTheme();
  const banner = useAppBanner();
  const { config } = useClueConfig();
  const loading = config.configuration === null;

  return (
    <PageCardCentered>
      <Box color={theme.palette.primary.main} fontSize="30pt">
        {banner}
      </Box>
      {loading && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <CircularProgress />
        </div>
      )}

      {config.configuration?.auth?.oauth_providers?.length > 0 && (
        <OAuthLogin providers={config.configuration?.auth?.oauth_providers} />
      )}
    </PageCardCentered>
  );
};

export default LoginScreen;
