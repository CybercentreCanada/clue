import { Icon } from '@iconify/react';
import type { CardProps } from '@mui/material';
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  Stack,
  Tooltip,
  Typography,
  useTheme
} from '@mui/material';
import { ClueComponentContext } from 'lib/hooks/ClueComponentContext';
import { useClueEnrichSelector } from 'lib/hooks/selectors';
import useAnnotations from 'lib/hooks/useAnnotations';
import useErrors from 'lib/hooks/useErrors';
import AssessmentIcon from 'lib/icons/Assessment';
import ContextIcon from 'lib/icons/Context';
import OpinionIcon from 'lib/icons/Opinion';
import { ICON_MAP } from 'lib/icons/iconMap';
import FrequencyText from 'lib/text/Frequency';
import uniq from 'lodash-es/uniq';
import type { FC } from 'react';
import { memo, useCallback, useMemo, useState } from 'react';
import { useContextSelector } from 'use-context-selector';
import AnnotationEntry from './AnnotationEntry';
import ExecutePopover from './actions/ExecutePopover';
import EnrichPopover from './enrichment/EnrichPopover';

export interface EnrichedCardProps {
  type: string;
  value: string;
  classification?: string;
  contextIcon?: boolean;
  counters?: boolean;
  hideLoading?: boolean;
}

const EnrichedCard: FC<EnrichedCardProps & CardProps> = ({
  type,
  value,
  classification: _classification,
  contextIcon = false,
  counters = false,
  hideLoading = false,
  ...otherProps
}) => {
  const theme = useTheme();
  const { t } = useContextSelector(ClueComponentContext, ctx => ctx.i18next);

  const defaultClassification = useClueEnrichSelector(ctx => ctx.defaultClassification);
  const enrich = useClueEnrichSelector(state => state.enrich);

  const [filter, setFilter] = useState<string>('all');

  const classification = useMemo(
    () => _classification ?? defaultClassification,
    [_classification, defaultClassification]
  );

  const [annotations, loading] = useAnnotations(type, value, classification);
  const errors = useErrors(value);
  const enrichRequest = { type, value, classification };

  const options = useMemo(() => ['all', ...uniq(annotations.map(annotation => annotation.type))], [annotations]);

  const forceEnrich = useCallback(() => {
    return enrich(type, value, {
      classification: classification,
      timeout: 15,
      force: true
    });
  }, [classification, enrich, type, value]);

  return (
    <Card
      sx={[
        {
          maxWidth: '900px'
        },
        ...(Array.isArray(otherProps?.sx) ? otherProps?.sx : [otherProps?.sx])
      ]}
      {...otherProps}
    >
      <CardHeader
        title={
          <Stack direction="row" spacing={1} alignItems="center">
            <FrequencyText annotations={annotations} value={value} variant="h6" />
            <AssessmentIcon
              value={enrichRequest}
              annotations={annotations}
              counters={counters}
              fontSize="1em"
              disableTooltip
            />
            <OpinionIcon
              value={enrichRequest}
              annotations={annotations}
              counters={counters}
              fontSize="1em"
              disableTooltip
            />
            <ContextIcon
              value={enrichRequest}
              annotations={annotations}
              counters={counters}
              showExtraIcon={contextIcon}
              fontSize="inherit"
              disableTooltip
            />
            {loading && !hideLoading && <CircularProgress color="primary" size={18} />}
            <div style={{ flex: 1 }} />
            <EnrichPopover selector={enrichRequest} />
            <ExecutePopover selectors={[enrichRequest]} />
          </Stack>
        }
      />
      <Divider sx={{ mx: 1 }} />
      <CardContent sx={{ p: 1 }}>
        <Grid container spacing={0.5} sx={{ mb: 1 }}>
          {options.map((opt, id) => (
            // eslint-disable-next-line react/no-array-index-key
            <Grid item key={id}>
              <Chip
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
            </Grid>
          ))}
          {errors?.length > 0 && (
            <Grid item>
              <Tooltip
                title={
                  <div onClick={e => e.stopPropagation()}>
                    {errors.map(err => (
                      <div key={err.source}>
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
                  icon={
                    <Icon
                      icon="material-symbols:timer-outline"
                      color={theme.palette.error.main}
                      style={{ filter: 'drop-shadow(0px 0px 1px rgb(0 0 0 / 0.4))' }}
                    />
                  }
                  label={
                    <Typography variant="caption" textTransform="capitalize">
                      {t('annotation.failed')}: {errors.length}
                    </Typography>
                  }
                  onClick={forceEnrich}
                />
              </Tooltip>
            </Grid>
          )}
        </Grid>
        <Grid container spacing={1} alignItems="stretch">
          {annotations.map((annotation, id) => (
            // eslint-disable-next-line react/no-array-index-key
            <Grid key={id} item xs={6} minWidth="300px">
              <Box sx={{ border: `thin solid ${theme.palette.divider}`, p: 1, height: '100%' }}>
                <AnnotationEntry annotation={annotation} />
              </Box>
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
};

export default memo(EnrichedCard);
