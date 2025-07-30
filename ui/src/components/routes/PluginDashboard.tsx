import { HelpCenter, OpenInNew } from '@mui/icons-material';
import SearchIcon from '@mui/icons-material/Search';
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Divider,
  Grid2 as Grid,
  IconButton,
  InputAdornment,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography
} from '@mui/material';
import api from 'api';
import type { DocumentationResponse } from 'api/static/documentation';
import PageCenter from 'commons/components/pages/PageCenter';
import Fuse from 'fuse.js';
import { useClueEnrichSelector, useClueFetcherSelector } from 'lib/hooks/selectors';
import useClueActions from 'lib/hooks/useClueActions';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

const PluginDashboard = () => {
  const [docs, setDocs] = useState<DocumentationResponse>({});
  const [docsList, setDocsList] = useState<string[]>(Object.keys(docs) ?? []);
  const [fetchersList, setFetchersList] = useState({});
  const [actionsList, setActionsList] = useState({});
  const [displayAllDocs, setDisplayAllDocs] = useState('all');
  const { t } = useTranslation();
  const availableSources = useClueEnrichSelector(ctx => ctx.availableSources);
  const { availableActions } = useClueActions();
  const fetchers = useClueFetcherSelector(ctx => ctx.fetchers);

  const fuse = useMemo(
    () =>
      new Fuse(Object.keys(docs), {
        keys: ['name', 'category'],
        threshold: 0.3
      }),
    [docs]
  );

  useEffect(() => {
    if (availableActions) {
      setActionsList(availableActions);
    }

    if (fetchers) {
      setFetchersList(fetchers);
    }
  }, [availableActions, fetchers]);

  useEffect(() => {
    (async () => {
      const _info = await api._static.all_documentation.get('-docs');

      if (_info) {
        setDocsList(Object.keys(_info));
        setDocs(_info);
      }
    })();
  }, []);

  const fzfSearch = useCallback(
    (searchedVal: string) => {
      if (searchedVal === '') {
        setDocsList(Object.keys(docs));
      } else {
        const searchResults = fuse.search(searchedVal).map(_entry => _entry.item);
        setDocsList(searchResults);
      }
    },
    [docs, fuse]
  );

  const getAvailableSourcesDocs = (_event: React.MouseEvent<HTMLElement>, showdoc: string) => {
    setDisplayAllDocs(showdoc);

    if (showdoc === 'active') {
      const availableSourcesDocs = docsList.filter(item =>
        availableSources.some(substring => item.includes(substring))
      );

      setDocsList(availableSourcesDocs);
    } else {
      setDocsList(Object.keys(docs));
    }
  };

  const getSummary = (pluginDoc: string) => {
    const summary = docs[pluginDoc].match(/Summary:\s*(.+)/)?.[1] ?? t('summary.unfound');
    return summary.replaceAll('*', '');
  };

  const getPluginFetchersandActions = (pluginName: string) => {
    const plugin = pluginName.split('-docs')[0].slice(0);

    const foundFetchers = Object.keys(fetchersList)
      .filter(key => key.split('.')[0] === plugin)
      .reduce((fetcher, key) => {
        fetcher[key] = fetchersList[key];
        return fetcher;
      }, {});

    const foundActions = Object.keys(actionsList)
      .filter(key => key.split('.')[0] === plugin)
      .reduce((action, key) => {
        action[key] = fetchersList[key];
        return action;
      }, {});

    const lengthOfFetchers = Object.keys(foundFetchers).length;
    const lengthOfActions = Object.keys(foundActions).length;

    return (
      <>
        <Typography sx={{ marginTop: 1, marginBottom: 1 }}>{t('route.fetchers.available')}</Typography>
        {lengthOfFetchers > 0 ? (
          Object.keys(foundFetchers).map(key => (
            <Tooltip key={key} title={fetchersList[key].description}>
              <Chip label={key.split('.')[1]} variant="outlined" size="small" color="primary" />
            </Tooltip>
          ))
        ) : (
          <Chip label="None" variant="outlined" size="small" />
        )}

        <Typography sx={{ marginTop: 1, marginBottom: 1 }}>{t('action.available')}</Typography>
        {lengthOfActions > 0 ? (
          Object.keys(foundActions).map(key => (
            <Tooltip key={key} title={actionsList[key].summary}>
              <Chip label={key.split('.')[1]} variant="outlined" size="small" color="primary" />
            </Tooltip>
          ))
        ) : (
          <Chip label="None" variant="outlined" size="small" />
        )}
      </>
    );
  };

  const getActivityStatus = (pluginName: string) => {
    const plugin = pluginName.split('-docs')[0].slice(0);

    const activeStatus = availableSources.find(source => source.includes(plugin));

    return activeStatus ? (
      <Chip label="Active" variant="outlined" size="small" color="success" />
    ) : (
      <Chip label="Inactive" variant="outlined" size="small" sx={{ color: 'grey' }} />
    );
  };

  const getDocumentationTitle = (pluginName: string) => {
    const plugin = pluginName.split('-docs')[0].slice(0);
    return plugin
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <PageCenter margin={4} width="100%" maxWidth="1750px" textAlign="left">
      <Stack spacing={1}>
        <Typography variant="h3" sx={{ display: 'flex', flexDirection: 'row', alignItems: 'center' }}>
          <HelpCenter fontSize="inherit" sx={{ mr: 1 }} />
          <span>{t('route.help.dashboard')}</span>
          <ToggleButtonGroup
            value={displayAllDocs}
            color="primary"
            exclusive
            onChange={getAvailableSourcesDocs}
            size="large"
            sx={{ display: 'flex', ml: 'auto', mr: 1 }}
          >
            <ToggleButton value="all" sx={{ minWidth: '100px' }}>
              {t('all')}
            </ToggleButton>
            <ToggleButton value="active" sx={{ minWidth: '100px' }}>
              {t('route.plugin.active')}
            </ToggleButton>
          </ToggleButtonGroup>
          <TextField
            id="outlined-basic"
            label="Search plugins"
            variant="outlined"
            onChange={event => fzfSearch(event.target.value)}
            sx={{ display: 'flex' }}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                )
              }
            }}
          />
        </Typography>

        <Divider />
        <Grid container spacing={2}>
          {docsList.map(key => (
            <Grid size={{ xs: 12, md: 6, lg: 4, xl: 3 }} key={key}>
              <Card
                sx={{
                  minWidth: 300,
                  minHeight: 300,
                  height: '100%'
                }}
              >
                <CardHeader
                  title={
                    <Stack
                      direction="column"
                      spacing={1}
                      sx={{ '& svg': { fontSize: 'inherit' }, '& > span': { ml: 1 } }}
                    >
                      <Stack direction="row" alignItems="center">
                        <Typography variant="h5">
                          {getDocumentationTitle(key)} {t('route.plugin')}
                        </Typography>
                        <IconButton sx={{ ml: 'auto' }} component={Link} to={`/help/${key.replace('.md', '')}`}>
                          <OpenInNew color="primary" fontSize="inherit" />
                        </IconButton>
                      </Stack>

                      <Box sx={{ display: 'inline-flex', alignItems: 'center' }}>{getActivityStatus(key)}</Box>
                    </Stack>
                  }
                />
                <CardContent>
                  <Typography>{getSummary(key)}</Typography>
                  <Divider sx={{ marginTop: 1 }} />
                  {getPluginFetchersandActions(key)}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Stack>
    </PageCenter>
  );
};

export default PluginDashboard;
