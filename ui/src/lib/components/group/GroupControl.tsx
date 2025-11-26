import { Autocomplete, Box, Button, Card, CircularProgress, Stack, TextField, Typography } from '@mui/material';
import FlexOne from 'commons/addons/flexers/FlexOne';
import Iconified from 'lib/components/display/icons/Iconified';
import type { SnackbarEvents } from 'lib/data/event';
import { SNACKBAR_EVENT_ID } from 'lib/data/event';
import { ClueGroupContext } from 'lib/hooks/ClueGroupContext';
import { useClueComponentSelector, useClueEnrichSelector } from 'lib/hooks/selectors';
import { safeDispatchEvent } from 'lib/utils/window';
import capitalize from 'lodash-es/capitalize';
import type { FC } from 'react';
import { useCallback, useMemo, useState } from 'react';
import { useContextSelector } from 'use-context-selector';
import ExecutePopover from '../actions/ExecutePopover';

const GroupControl: FC = () => {
  const { t } = useClueComponentSelector(ctx => ctx.i18next);

  const { type, values, classification } = useContextSelector(ClueGroupContext, ctx => ({
    type: ctx?.type,
    values: ctx?.values,
    classification: ctx?.classification
  }));
  const sources = useClueEnrichSelector(ctx => ctx.availableSources);
  const enrich = useClueEnrichSelector(ctx => ctx.bulkEnrich);

  const [loading, setLoading] = useState(false);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);

  const fullValues = useMemo(
    () => (values ?? []).map(value => ({ value, type, classification })),
    [classification, type, values]
  );

  const runEnrichment = useCallback(async () => {
    if (loading) {
      return;
    }

    try {
      setLoading(true);
      await enrich(
        (values ?? []).map(value => ({ type, value })),
        { force: true, sources: selectedSources }
      );
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error(e);
      safeDispatchEvent(
        new CustomEvent<SnackbarEvents>(SNACKBAR_EVENT_ID, {
          detail: {
            message: e.toString(),
            level: 'error'
          }
        })
      );
    } finally {
      setLoading(false);
    }
  }, [enrich, loading, selectedSources, type, values]);

  return (
    <Card sx={{ p: 1 }}>
      <Stack direction="row" spacing={1} alignItems="center">
        <Box
          sx={theme => ({
            border: 'thin solid',
            alignSelf: 'stretch',
            display: 'flex',
            alignItems: 'center',
            px: 1,
            borderRadius: '5px',
            borderColor: theme.palette.divider
          })}
        >
          <Typography color="text.secondary">
            {values?.length ?? 0} {t('selected')}
          </Typography>
        </Box>
        <FlexOne />
        <Autocomplete
          size="small"
          multiple
          options={sources}
          sx={{ minWidth: '400px' }}
          renderInput={params => <TextField size="small" placeholder={t('sources')} {...params} />}
          value={selectedSources}
          onChange={(__, value) => setSelectedSources(value)}
          disableCloseOnSelect
          getOptionLabel={opt =>
            opt
              .split(/[_-]/)
              .map(word => capitalize(word))
              .join(' ')
          }
        />
        <Button
          variant="outlined"
          color="info"
          disabled={values?.length < 1 || loading}
          startIcon={
            loading ? <CircularProgress color="info" size="20px" /> : <Iconified icon="ic:outline-play-arrow" />
          }
          sx={{ alignSelf: 'stretch' }}
          onClick={runEnrichment}
        >
          {t('enrich')}
        </Button>
        <ExecutePopover selectors={fullValues} size="medium" multiples />
      </Stack>
    </Card>
  );
};

export default GroupControl;
