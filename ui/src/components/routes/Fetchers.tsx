import { Landscape, PlayArrow } from '@mui/icons-material';
import { Autocomplete, Button, Grid, LinearProgress, ListItemText, Stack, TextField, Typography } from '@mui/material';
import PageCenter from 'commons/components/pages/PageCenter';
import Fetcher from 'lib/components/fetchers/Fetcher';
import { useClueFetcherSelector } from 'lib/hooks/selectors';
import useClueConfig from 'lib/hooks/useClueConfig';
import type { Selector } from 'lib/types/lookup';
import uniq from 'lodash-es/uniq';
import type { FC } from 'react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

interface FetcherAndSelector extends Selector {
  fetcherId: string;
}

const Fetchers: FC = () => {
  const { t } = useTranslation();
  const { config } = useClueConfig();
  const fetchers = useClueFetcherSelector(ctx => ctx.fetchers);
  const fetchCompleted = useClueFetcherSelector(ctx => ctx.fetchCompleted);

  const [fetcher, setFetcher] = useState('');
  const [classification, setClassification] = useState(config.c12nDef.RESTRICTED.replace(/\/\/.+/, ''));
  const [type, setType] = useState('');
  const [value, setValue] = useState('');
  const [selectors, setSelectors] = useState<FetcherAndSelector[]>([]);

  return (
    <PageCenter maxWidth="1800px" textAlign="left" height="100%">
      <Stack spacing={1}>
        <Typography variant="h3" sx={{ flex: 1 }}>
          {t('route.fetchers')}
        </Typography>
        <Stack direction="row" spacing={1}>
          <Autocomplete
            size="small"
            disabled={!fetchCompleted}
            fullWidth
            value={fetcher}
            options={Object.keys(fetchers).filter(
              fetcherId => !type || fetchers[fetcherId].supported_types.includes(type)
            )}
            onChange={(__, fetcherValue) => setFetcher(fetcherValue)}
            renderInput={params => (
              <TextField {...params} sx={{ minWidth: '250px' }} label={t('route.fetchers.fetcher')} />
            )}
            renderOption={({ key, ...props }, option) => (
              <ListItemText
                key={key}
                {...(props as any)}
                sx={{ flexDirection: 'column', alignItems: 'start !important' }}
                primary={option}
                secondary={fetchers[option]?.description}
              />
            )}
            sx={{ flex: 1 }}
            slotProps={{ paper: { sx: { minWidth: '600px' } } }}
          />
          <Autocomplete
            size="small"
            disabled={!fetchCompleted}
            fullWidth
            value={classification}
            options={Object.keys(config.c12nDef.levels_map_lts)}
            onChange={(__, classificationValue) => setClassification(classificationValue)}
            renderInput={params => (
              <TextField {...params} sx={{ minWidth: '250px' }} label={t('page.home.classification')} />
            )}
            renderOption={(props, option) => (
              <ListItemText
                {...(props as any)}
                sx={{ flexDirection: 'column', alignItems: 'start !important' }}
                primary={option}
                secondary={config.c12nDef.description[option]}
              />
            )}
            sx={{ flex: 1 }}
            slotProps={{ paper: { sx: { minWidth: '600px' } } }}
          />
          <Autocomplete
            size="small"
            sx={{ flex: 1 }}
            value={type}
            onChange={(_, typeValue) => setType(typeValue)}
            options={uniq(
              Object.entries(fetchers)
                .filter(([_fetcherId]) => !fetcher || _fetcherId === fetcher)
                .flatMap(([_, _fetcher]) => _fetcher.supported_types)
            )}
            renderInput={props => <TextField {...props} placeholder={t('route.fetchers.type')} />}
          />
        </Stack>
        <Stack direction="row" spacing={1}>
          <TextField
            size="small"
            disabled={!fetchCompleted}
            fullWidth
            sx={{ flex: 1 }}
            label={t('route.fetchers.value')}
            value={value}
            onChange={event => setValue(event.target.value)}
            onKeyDown={event =>
              event.ctrlKey &&
              event.key === 'Enter' &&
              setSelectors(_selectors => [..._selectors, { type, value, classification, fetcherId: fetcher }])
            }
          />
          <Button
            disabled={!(type && value && classification && fetcher)}
            startIcon={<PlayArrow />}
            variant="outlined"
            color="success"
            onClick={() =>
              setSelectors(_selectors => [..._selectors, { type, value, classification, fetcherId: fetcher }])
            }
          >
            {t('route.fetchers.submit')}
          </Button>
        </Stack>
        <LinearProgress sx={{ opacity: fetchCompleted ? 0 : 1 }} />
        <Grid
          container
          spacing={1}
          sx={theme => ({ marginLeft: `${theme.spacing(-1)} !important`, marginTop: '0 !important' })}
        >
          {selectors.map(selector => (
            <Grid key={selector.fetcherId + selector.value} item xs={selector.fetcherId.endsWith('graph') ? 12 : 6}>
              <Fetcher
                fetcherId={selector.fetcherId}
                type={selector.type}
                value={selector.value}
                classification={selector.classification}
                slotProps={{ image: { style: { height: '500px' } } }}
              />
            </Grid>
          ))}
        </Grid>
        {!selectors?.length && (
          <Stack
            direction="column"
            spacing={2}
            sx={theme => ({
              height: '60vh',
              borderStyle: 'dashed',
              borderColor: theme.palette.text.secondary,
              borderWidth: '1rem',
              borderRadius: '1rem',
              opacity: 0.3,
              justifyContent: 'center',
              alignItems: 'center',
              padding: 3
            })}
          >
            <Typography variant="h1" sx={{ display: 'flex', alignItems: 'center' }}>
              <Stack
                direction="row"
                spacing={2.5}
                sx={{
                  '& svg': {
                    fontSize: '7rem'
                  }
                }}
              >
                <Landscape />
                <span>{t('route.fetchers.title')}</span>
              </Stack>
            </Typography>
            <Typography variant="h4" sx={{ textAlign: 'center' }}>
              {t('route.fetchers.description')}
            </Typography>
          </Stack>
        )}
      </Stack>
    </PageCenter>
  );
};

export default Fetchers;
