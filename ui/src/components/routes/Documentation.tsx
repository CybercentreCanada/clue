/* eslint-disable react/jsx-no-literals */
import { Box, LinearProgress, Typography } from '@mui/material';
import api from 'api';
import PageCenter from 'commons/components/pages/PageCenter';
import useMyApi from 'components/hooks/useMyApi';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import Markdown from 'react-markdown';
import { useParams } from 'react-router-dom';

const Documentation = () => {
  const { dispatchApi } = useMyApi();
  const params = useParams();
  const [docs, setDocs] = useState('');
  const { t } = useTranslation();

  const getDocumentation = useCallback(
    async (fileName: string) => {
      const fetchedDoc = (
        await Promise.all([
          dispatchApi(api._static.documentation.get(fileName)),
          new Promise(res => setTimeout(res, 200))
        ])
      )[0];

      setDocs(fetchedDoc.markdown);
    },
    [dispatchApi]
  );

  useEffect(() => {
    getDocumentation(params.pluginId);
  }, [getDocumentation, params.pluginId]);

  return docs ? (
    <PageCenter>
      <Box margin={4} width="100%" textAlign="left">
        <Markdown>{docs}</Markdown>
      </Box>
    </PageCenter>
  ) : (
    <>
      <LinearProgress sx={{ opacity: docs ? 0 : 1 }} />
      <Typography variant="h3" sx={{ textAlign: 'center' }}>
        {t('route.help.loading')}...
      </Typography>
    </>
  );
};

export default Documentation;
