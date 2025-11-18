/* eslint-disable react/jsx-no-literals */
import { ExpandLess, ExpandMore, PlayArrow } from '@mui/icons-material';
import {
  Alert,
  AlertTitle,
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  Collapse,
  Divider,
  FormControlLabel,
  IconButton,
  LinearProgress,
  ListItemText,
  Skeleton,
  Slider,
  Stack,
  TextField,
  Typography
} from '@mui/material';
import FlexOne from 'commons/addons/flexers/FlexOne';
import useAppTheme from 'commons/components/app/hooks/useAppTheme';
import PageCenter from 'commons/components/pages/PageCenter';
import AnnotationDetails from 'lib/components/AnnotationDetails';
import JSONViewer from 'lib/components/display/json';
import EnrichedTypography from 'lib/components/EnrichedTypography';
import SourcePicker from 'lib/components/SourcePicker';
import QueryStatus from 'lib/components/stats/QueryStatus';
import useClue from 'lib/hooks/useClue';
import useClueConfig from 'lib/hooks/useClueConfig';
import type { BulkEnrichResponses, EnrichResponse, EnrichResponses } from 'lib/types/lookup';
import isEmpty from 'lodash-es/isEmpty';
import range from 'lodash-es/range';
import type { FC } from 'react';
import { memo, useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import QueryInput from './QueryInput';

const SLIDER_MARKS = range(0, 110, 10).map(value => ({ value, label: value.toString() + 's' }));

const PluginResultCard: FC<{
  type: string;
  value: string;
  source: string;
  sourceResult: EnrichResponse;
}> = memo(({ type, value, source, sourceResult }) => {
  const [visible, setVisible] = useState<{ [key: string]: boolean }>({});
  const toggleVisible = key => {
    setVisible(cur_visible => ({ ...cur_visible, [key]: !cur_visible[key] }));
  };

  return (
    <Card variant="outlined" sx={theme => (sourceResult.error ? { borderColor: theme.palette.error.light } : null)}>
      <Stack
        direction="row"
        spacing={1}
        alignItems={'center'}
        p={1}
        onClick={() => toggleVisible(type + value + source)}
        sx={theme => ({
          cursor: 'pointer',
          '&:hover': {
            backgroundColor: theme.palette.action.hover
          }
        })}
      >
        <Typography variant="body1" noWrap sx={{ textTransform: 'capitalize', width: '100%' }}>
          {source}
        </Typography>
        <IconButton>{visible[type + value + source] ? <ExpandLess /> : <ExpandMore />}</IconButton>
      </Stack>
      <Collapse in={visible[type + value + source]}>
        <CardContent>
          {sourceResult.error ? (
            <Alert variant="outlined" severity="error">
              {sourceResult.error}
            </Alert>
          ) : (
            <JSONViewer data={sourceResult} forceCompact collapse={false} />
          )}
        </CardContent>
      </Collapse>
    </Card>
  );
});

const ItemResultCard: FC<{ type: string; value: string; classification?: string; queryResult: EnrichResponses }> = memo(
  ({ type, value, classification, queryResult }) => {
    const [visible, setVisible] = useState<{ [key: string]: boolean }>({});

    const toggleVisible = useCallback(key => {
      setVisible(cur_visible => ({ ...cur_visible, [key]: !cur_visible[key] }));
    }, []);

    return (
      <Card sx={theme => ({ border: `1px solid ${theme.palette.divider}` })}>
        <Stack
          direction="row"
          spacing={1}
          alignItems="center"
          px={1.75}
          pt={0.75}
          pb={0.5}
          onClick={() => toggleVisible(type + value)}
          sx={theme => ({
            cursor: 'pointer',
            '&:hover': {
              backgroundColor: theme.palette.action.hover
            }
          })}
        >
          <Typography color="text.secondary" variant="h6">
            {type.toUpperCase()}:
          </Typography>
          <EnrichedTypography type={type} value={value} variant="h6" hideDetails contextIcon counters />
          <Box sx={{ width: '100%' }}></Box>
          <IconButton size="small">
            <ExpandMore
              sx={theme => ({
                transform: visible[type + value] ? 'rotate(180deg)' : 'rotate(0deg)',
                transition: theme.transitions.create('transform')
              })}
            />
          </IconButton>
        </Stack>

        <Collapse in={visible[type + value]}>
          <CardContent sx={{ pt: 0.5 }}>
            <Stack spacing={1}>
              <Card variant="outlined">
                <AnnotationDetails enrichRequest={{ type, value, classification }} />
              </Card>
              <Typography variant="h6" pt={2}>
                Detailed Plugin Results:
              </Typography>
              {Object.entries(queryResult).map(([source, sourceResult]) => (
                <PluginResultCard
                  key={type + value + source}
                  type={type}
                  value={value}
                  source={source}
                  sourceResult={sourceResult}
                />
              ))}
            </Stack>
          </CardContent>
        </Collapse>
      </Card>
    );
  }
);

const EnrichmentResults: FC<{ queryResults: BulkEnrichResponses; classification?: string }> = memo(
  ({ queryResults, classification }) => {
    return Object.entries(queryResults).map(([data_type, entries]) => (
      <Stack key={data_type} spacing={1}>
        {Object.entries(entries).map(([data_value, queryResult]) => (
          <ItemResultCard
            key={data_type + data_value}
            type={data_type}
            value={data_value}
            classification={classification}
            queryResult={queryResult}
          />
        ))}
      </Stack>
    ));
  }
);

const Home: FC = () => {
  const { isDark } = useAppTheme();
  const { t } = useTranslation('clue');
  const { bulkEnrich, typesDetection, guessType } = useClue();
  const { config } = useClueConfig();

  const [queryResults, setQueryResults] = useState<BulkEnrichResponses>({});
  const [loading, setLoading] = useState(true);
  const [customTimeout, setCustomTimeout] = useState(false);
  const [includeRaw, setIncludeRaw] = useState(false);
  const [noCache, setNoCache] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [timeout, setTimeout] = useState(5);
  const [classification, setClassification] = useState(config.c12nDef.RESTRICTED.replace(/\/\/.+/, ''));
  const [enrichQuery, setSearchQuery] = useState('');

  const onSubmit = useCallback(async () => {
    const query = [];
    const _errors = [];
    for (const value of enrichQuery.split('\n')) {
      if (value) {
        const trimmedValue = value.replaceAll(' ', '');
        const matchedKey = Object.keys(typesDetection).find(key => trimmedValue.startsWith(key + ':'));
        const detectedType = matchedKey ? trimmedValue.slice(0, matchedKey.length) : guessType(trimmedValue);

        if (detectedType && matchedKey) {
          query.push({
            type: detectedType,
            value: trimmedValue.slice(matchedKey.length + 1, trimmedValue.length)
          });
        } else if (detectedType && !matchedKey) {
          query.push({ type: detectedType, value: trimmedValue });
        } else {
          _errors.push(trimmedValue);
        }
      }
    }

    try {
      setLoading(true);
      setQueryResults(
        await bulkEnrich(query, { timeout: customTimeout ? timeout : null, includeRaw, noCache, classification })
      );
    } finally {
      setErrors(_errors);
      setLoading(false);
    }
  }, [enrichQuery, typesDetection, guessType, bulkEnrich, customTimeout, timeout, includeRaw, noCache, classification]);

  useEffect(() => {
    if (Object.keys(typesDetection).length === 0) {
      setLoading(true);
    } else {
      setLoading(false);
    }
  }, [typesDetection]);

  return (
    <PageCenter textAlign="left" height="100%" width="100%" maxWidth="1500px">
      <Stack spacing={1}>
        <Stack direction="row" alignItems="center" spacing={1}>
          <img src={`/svg/${isDark ? 'dark' : 'light'}/clue-icon2-simple.svg`} alt="Clue" style={{ height: '48px' }} />
          <Typography variant="h3" color="textSecondary">
            Clue
          </Typography>
        </Stack>
        <Typography variant="body1" sx={{ whiteSpace: 'nowrap' }}>
          {t('page.home.types')}:
        </Typography>
        <Stack direction="row" spacing={0.5}>
          {loading && isEmpty(Object.keys(typesDetection))
            ? range(0, 3).map(v => <Skeleton key={v} variant="rounded" height="24px" width="50px" />)
            : Object.keys(typesDetection).map(type => <Chip key={type} size="small" label={type} />)}
        </Stack>
        <LinearProgress sx={theme => ({ transition: theme.transitions.create('opacity'), opacity: +loading })} />
        <Stack position="relative">
          <QueryInput
            width="100%"
            height="250px"
            query={enrichQuery}
            setQuery={setSearchQuery}
            onSubmit={onSubmit}
            loading={loading}
          />
          <Box
            sx={{
              position: 'absolute',
              left: '100%',
              width: '200px'
            }}
          >
            <QueryStatus />
          </Box>
        </Stack>
        <Stack direction="row" alignItems="center" spacing={1}>
          <SourcePicker />
          <Divider flexItem orientation="vertical" />
          <Autocomplete
            size="small"
            fullWidth
            value={classification}
            options={Object.keys(config.c12nDef.levels_map_lts)}
            onChange={(__, value) => setClassification(value)}
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
            sx={{ maxWidth: '300px' }}
            slotProps={{ paper: { sx: { minWidth: '600px' } } }}
          />
          <Divider flexItem orientation="vertical" />
          <FormControlLabel
            control={
              <Checkbox size="small" checked={customTimeout} onChange={(__, checked) => setCustomTimeout(checked)} />
            }
            label={
              <Typography ml={0.5} variant="caption">
                {t('page.home.timeout')}
              </Typography>
            }
            sx={theme => ({ whiteSpace: 'nowrap', color: theme.palette.text.secondary, pr: 1 })}
          />
          <Divider flexItem orientation="vertical" />
          <FormControlLabel
            control={<Checkbox size="small" checked={includeRaw} onChange={(__, checked) => setIncludeRaw(checked)} />}
            label={
              <Typography ml={0.5} variant="caption">
                {t('page.home.includeraw')}
              </Typography>
            }
            sx={theme => ({ whiteSpace: 'nowrap', color: theme.palette.text.secondary, pr: 1 })}
          />
          <Divider flexItem orientation="vertical" />
          <FormControlLabel
            control={<Checkbox size="small" checked={noCache} onChange={(__, checked) => setNoCache(checked)} />}
            label={
              <Typography ml={0.5} variant="caption">
                {t('page.home.cache')}
              </Typography>
            }
            sx={theme => ({ whiteSpace: 'nowrap', color: theme.palette.text.secondary, pr: 1 })}
          />
          <FlexOne />
          <Button
            disabled={loading || enrichQuery === ''}
            onClick={onSubmit}
            variant="outlined"
            color="success"
            startIcon={<PlayArrow />}
          >
            {t('enrich')}
          </Button>
        </Stack>
        {customTimeout && (
          <Box>
            <Slider
              min={1}
              max={50}
              step={1}
              shiftStep={5}
              marks={SLIDER_MARKS}
              getAriaValueText={val => val.toString() + 's'}
              value={timeout}
              onChange={(__, value) => setTimeout(value as number)}
              valueLabelFormat={value => value.toString() + 's'}
              valueLabelDisplay="auto"
            />
          </Box>
        )}
        {errors.length !== 0 && (
          <Alert variant="outlined" severity="error">
            <AlertTitle>ERROR: Could not identify the type of the following items:</AlertTitle>
            <ul>
              {errors.map(name => (
                <li key={name}>{name}</li>
              ))}
            </ul>
          </Alert>
        )}
        <EnrichmentResults queryResults={queryResults} classification={classification} />
      </Stack>
    </PageCenter>
  );
};

export default Home;
