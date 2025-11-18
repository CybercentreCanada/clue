/* eslint-disable react/jsx-no-literals */
import { Typography } from '@mui/material';
import api from 'api';
import PageCenter from 'commons/components/pages/PageCenter';
import useMyApi from 'components/hooks/useMyApi';
import Markdown from 'lib/components/display/markdown';
import type { FC } from 'react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

const Contributing: FC = () => {
  const { dispatchApi } = useMyApi();

  const [docs, setDocs] = useState('');
  const [error, setError] = useState<Error>(null);
  const { i18n, t } = useTranslation();

  useEffect(() => {
    (async () => {
      const textLanguage = i18n.language === 'en' ? 'en' : 'fr';

      try {
        const _info = (
          await Promise.all([
            dispatchApi(api._static.documentation.get('api/CONTRIBUTING.' + textLanguage + '.md')),
            new Promise(res => setTimeout(res, 200))
          ])
        )[0];

        if (_info) {
          setDocs(_info.markdown);
        }
      } catch (e) {
        setError(e);
        // eslint-disable-next-line no-console
        console.error(e);
      }
    })();
  }, [dispatchApi, i18n.language]);

  return docs ? (
    <PageCenter margin={4} width="100%" textAlign="left">
      <Markdown md={docs} />
    </PageCenter>
  ) : error ? (
    <Typography variant="h3" sx={{ textAlign: 'center' }}>
      {t('route.help.error')}
    </Typography>
  ) : (
    <Typography variant="h3" sx={{ textAlign: 'center' }}>
      {t('route.help.loading')}...
    </Typography>
  );
};

export default Contributing;
