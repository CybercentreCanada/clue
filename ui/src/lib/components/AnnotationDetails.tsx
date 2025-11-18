/* eslint-disable react/no-array-index-key */
import { Icon } from '@iconify/react';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  Stack,
  Tooltip,
  Typography,
  useTheme
} from '@mui/material';
import Iconified from 'lib/components/display/icons/Iconified';
import type { SnackbarEvents } from 'lib/data/event';
import { SNACKBAR_EVENT_ID } from 'lib/data/event';
import { ClueComponentContext } from 'lib/hooks/ClueComponentContext';
import { useClueEnrichSelector } from 'lib/hooks/selectors';
import useAnnotations from 'lib/hooks/useAnnotations';
import useErrors from 'lib/hooks/useErrors';
import { ICON_MAP } from 'lib/icons/iconMap';
import type { Selector } from 'lib/types/lookup';
import { safeDispatchEvent } from 'lib/utils/window';
import groupBy from 'lodash-es/groupBy';
import isNull from 'lodash-es/isNull';
import uniq from 'lodash-es/uniq';
import type { FC } from 'react';
import { memo, useCallback, useEffect, useMemo, useState } from 'react';
import { useContextSelector } from 'use-context-selector';
import ExecutePopover from './actions/ExecutePopover';
import AnnotationEntry from './AnnotationEntry';
import ClassificationChip from './ClassificationChip';
import EnrichPopover from './enrichment/EnrichPopover';

/**
 * The Annotation Popover is for showing a permanent popover on click with interactivity. For showing data on hover, use Annotation Popper.
 */
const AnnotationDetails: FC<{
  enrichRequest: Selector;
  setReady?: (ready: boolean) => void;
  updatePosition?: () => void;
}> = ({ enrichRequest, setReady, updatePosition }) => {
  const theme = useTheme();

  const { t } = useContextSelector(ClueComponentContext, ctx => ctx.i18next);

  const [filter, setFilter] = useState<string>('all');

  const enrich = useClueEnrichSelector(state => state.enrich);

  const [annotations, loading] = useAnnotations(
    enrichRequest?.type,
    enrichRequest?.value,
    enrichRequest?.classification,
    { skipEnrichment: true }
  );
  const errors = useErrors(enrichRequest?.value);

  const options = useMemo(
    () => ['all', ...uniq((annotations ?? []).map(annotation => annotation.type))],
    [annotations]
  );
  const annotationsByType = useMemo(() => groupBy(annotations ?? [], 'type'), [annotations]);

  const forceEnrich = useCallback(async () => {
    await enrich(enrichRequest.type, enrichRequest.value, {
      classification: enrichRequest.classification,
      timeout: 15,
      force: true
    });
  }, [enrichRequest, enrich]);

  useEffect(() => {
    if (!setReady) {
      return;
    }

    setReady(enrichRequest && !isNull(annotations));
    updatePosition?.();
  }, [annotations, enrichRequest, setReady, updatePosition]);

  return (
    enrichRequest &&
    !isNull(annotations) && (
      <Stack direction="column" sx={{ p: 1, width: '100%' }} spacing={1}>
        <Stack spacing={1}>
          <Stack direction="row" spacing={1}>
            <Stack>
              <Stack direction="row" spacing={1}>
                <Typography variant="body1" fontWeight="bold">
                  {'Clue'}
                </Typography>
                {enrichRequest.classification && (
                  <ClassificationChip size="small" classification={enrichRequest.classification} />
                )}
              </Stack>
              <Typography variant="caption" color="text.secondary">
                {enrichRequest.type.toLocaleUpperCase()} {t('enrichment')}
              </Typography>
            </Stack>
            <div style={{ flex: 1 }} />
            <Tooltip title={t('refresh')}>
              <Box sx={{ alignSelf: 'center', m: -1 }}>
                <IconButton onClick={() => forceEnrich()} disabled={loading}>
                  {loading ? (
                    <CircularProgress variant="indeterminate" size={20} />
                  ) : (
                    <Iconified icon="ic:baseline-replay" fontSize="small" />
                  )}
                </IconButton>
              </Box>
            </Tooltip>
            <Tooltip title={t('clipboard')}>
              <IconButton
                sx={{ alignSelf: 'center', m: -1 }}
                onClick={() => {
                  navigator.clipboard.writeText(enrichRequest.value);
                  safeDispatchEvent(
                    new CustomEvent<SnackbarEvents>(SNACKBAR_EVENT_ID, {
                      detail: {
                        message: `${enrichRequest.value} ${t('clipboard.success')}`,
                        level: 'success'
                      }
                    })
                  );
                }}
              >
                <Iconified icon="ic:outline-assignment" fontSize="small" />
              </IconButton>
            </Tooltip>
            <EnrichPopover selector={enrichRequest} />
            <ExecutePopover selectors={[enrichRequest]} />
          </Stack>
          <Stack direction="row" spacing={0.5}>
            {options.map((opt, id) => (
              <Chip
                key={id}
                size="small"
                variant={opt === filter ? 'filled' : 'outlined'}
                icon={ICON_MAP[opt] && <Icon icon={ICON_MAP[opt]} />}
                label={
                  <Typography variant="caption" textTransform="capitalize">
                    {opt}:{' '}
                    {opt === 'all'
                      ? annotations.length
                      : annotations.filter(annotation => annotation.type === opt).length}
                  </Typography>
                }
                onClick={() => setFilter(opt)}
              />
            ))}
            {errors?.length > 0 && (
              <Tooltip
                title={
                  <div onClick={e => e.stopPropagation()}>
                    {errors.map((err, err_id) => (
                      <div key={err_id}>
                        <span style={{ textTransform: 'capitalize' }}>{err.source.replace(/-/g, ' ')}</span>:{' '}
                        {err.message}
                      </div>
                    ))}
                  </div>
                }
              >
                <Chip
                  size="small"
                  variant="outlined"
                  icon={<Icon icon="material-symbols:timer-outline" color={theme.palette.error.main} />}
                  label={
                    <Typography variant="caption" textTransform="capitalize">
                      {t('annotation.failed')}: {errors.length}
                    </Typography>
                  }
                  onClick={forceEnrich}
                />
              </Tooltip>
            )}
          </Stack>
        </Stack>
        <Box />
        {Object.keys(annotationsByType)
          .filter(type => !filter || filter === 'all' || type === filter)
          .map((type, id) => (
            <Accordion
              key={id}
              defaultExpanded
              sx={{
                marginTop: `${theme.spacing(1)} !important`,
                marginBottom: '0 !important',
                '&:before': { height: 0 }
              }}
            >
              {filter === 'all' && (
                <AccordionSummary
                  expandIcon={<Iconified icon="ic:baseline-arrow-drop-down" />}
                  sx={{
                    minHeight: 'initial !important',
                    mt: 0.5,
                    mb: 0,
                    px: 1,
                    '& .MuiAccordionSummary-content': { my: 0.5, mx: 0 },
                    '& .MuiAccordionSummary-content.Mui-expanded': { my: 0.5, mx: 0 }
                  }}
                >
                  <Typography variant="body1" key={type} textTransform="capitalize">
                    {type}
                  </Typography>
                </AccordionSummary>
              )}
              <AccordionDetails sx={{ px: 1 }}>
                {filter === 'all' && <Divider orientation="horizontal" sx={{ mb: 1 }} />}
                <Stack spacing={1} divider={<Divider orientation="horizontal" flexItem />}>
                  {annotationsByType[type].map((annotation, ann_id) => (
                    <AnnotationEntry key={ann_id} annotation={annotation} />
                  ))}
                </Stack>
              </AccordionDetails>
            </Accordion>
          ))}
      </Stack>
    )
  );
};

export default memo(AnnotationDetails);
