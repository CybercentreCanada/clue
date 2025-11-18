import { Box, Typography, useTheme } from '@mui/material';
import useAppBanner from 'commons/components/app/hooks/useAppBanner';
import useAppLayout from 'commons/components/app/hooks/useAppLayout';
import PageCardCentered from 'commons/components/pages/PageCardCentered';
import useMyLocalStorage from 'lib/hooks/useMyLocalStorage';
import type { FC } from 'react';
import { useTranslation } from 'react-i18next';

const Logout: FC = () => {
  const { t } = useTranslation();
  const theme = useTheme();
  const banner = useAppBanner();
  const layout = useAppLayout();
  const localStorage = useMyLocalStorage();

  // hide topnav and leftnav on logout.
  layout.hideMenus();

  // There is probably more stuff to be done to properly logout a user.
  setTimeout(() => {
    localStorage.clear();
    window.location.replace('/');
  }, 2000);

  return (
    <PageCardCentered>
      <Box textAlign="center">
        <Box color={theme.palette.primary.main} fontSize="30pt">
          {banner}
        </Box>
        <Typography>{t('page.logout')}</Typography>
      </Box>
    </PageCardCentered>
  );
};

export default Logout;
