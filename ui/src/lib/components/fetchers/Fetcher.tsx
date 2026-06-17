/* eslint-disable no-console */
import { Icon } from '@iconify/react';
import type { ChipProps, ModalProps, PaperProps, SkeletonProps, StackProps } from '@mui/material';
import { Chip, IconButton, LinearProgress, Paper, Skeleton, Stack, Tooltip, Typography, useTheme } from '@mui/material';
import FlexOne from 'commons/addons/flexers/FlexOne';
import Iconified from 'lib/components/display/icons/Iconified';
import { ClueComponentContext } from 'lib/hooks/ClueComponentContext';
import { useClueFetcherSelector } from 'lib/hooks/selectors';
import type { FetcherResult } from 'lib/types/fetcher';
import type { Selector } from 'lib/types/lookup';
import type { FC } from 'react';
import React, { memo, useEffect, useMemo, useRef, useState } from 'react';
import { useContextSelector } from 'use-context-selector';
import { FetcherResultView } from './FetcherResultView';
import PreviewModal from './PreviewModal';
import StatusChip from './StatusChip';

export interface FetcherProps extends Selector {
  fetcherId: string;
  slotProps?: {
    paper?: PaperProps;
    preview?: ModalProps;
    stack?: StackProps;
    image?: React.DetailedHTMLProps<React.ImgHTMLAttributes<HTMLImageElement>, HTMLImageElement>;
    chip?: ChipProps;
    skeleton?: SkeletonProps;
  };
}

const Fetcher: FC<FetcherProps> = React.memo(
  ({
    type,
    value,
    classification,
    fetcherId,
    slotProps: {
      paper: paperProps = {},
      preview: previewProps = {},
      stack: stackProps = {},
      image: imageProps = {},
      chip: chipProps = {},
      skeleton: skeletonProps = {}
    } = {}
  }) => {
    const theme = useTheme();
    const fetchers = useClueFetcherSelector(ctx => ctx.fetchers);
    const fetchSelector = useClueFetcherSelector(ctx => ctx.fetchSelector);
    const getFetcherStatus = useClueFetcherSelector(ctx => ctx.getFetcherStatus);
    const fetchCompleted = useClueFetcherSelector(ctx => ctx.fetchCompleted);

    const { t } = useContextSelector(ClueComponentContext, ctx => ctx?.i18next);

    const [result, setResult] = useState<FetcherResult | null>(null);
    const [loading, setLoading] = useState(true);
    const [showPreview, setShowPreview] = useState(false);

    const timeoutRef = useRef<NodeJS.Timeout | null>(null);

    const taskId = useMemo(() => result?.task_id, [result?.task_id]);

    useEffect(() => {
      if (result?.outcome !== 'pending' || !taskId) return;

      let cancelled = false;

      const poll = async () => {
        const res = await getFetcherStatus(fetcherId, taskId);

        if (!res) {
          setResult({ outcome: 'failure', done: true, error: 'Missing result', link: '' });
        } else if (res.outcome === 'success' || res.outcome === 'failure') {
          setResult({ ...res, done: true });
        } else {
          if (cancelled) return;
          setResult({ ...res });
          timeoutRef.current = setTimeout(poll, 2000);
        }
      };

      poll();

      return () => {
        cancelled = true;
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
      };
    }, [fetcherId, getFetcherStatus, result?.outcome, taskId]);

    useEffect(() => {
      (async () => {
        try {
          setLoading(true);
          setResult(await fetchSelector(fetcherId, { type, value, classification }));
        } catch {
          setResult({ outcome: 'failure', done: true, error: t('error.unexpected') });
        } finally {
          setLoading(false);
        }
      })();
    }, [classification, fetchSelector, fetcherId, t, type, value]);

    const resultAdditionalProps = useMemo(() => {
      if (result?.outcome === 'success' && result.format === 'image') {
        return { onClick: () => setShowPreview(true), ...imageProps };
      }
      return { result };
    }, [imageProps, result]);

    if (fetchCompleted) {
      if (!fetcherId) {
        console.warn('Missing fetcher Id. Component will not render.');
        return null;
      } else if (!fetcherId.includes('.')) {
        console.warn(
          "Invalid fetcher id. Must be in the format '<plugin_id>.<fetcher_id>'. Component will not render."
        );
        return null;
      } else if (!(fetcherId in fetchers)) {
        console.warn('Fetcher ID does not correspond to a registered fetcher. Component will not render.');
        return null;
      }
    } else {
      return null;
    }

    if (loading) {
      if (fetchers[fetcherId]?.format === 'status') {
        return (
          <Skeleton
            variant="rounded"
            height="32px"
            width="150px"
            {...skeletonProps}
            sx={[
              { borderRadius: '16px' },
              ...(Array.isArray(skeletonProps?.sx) ? skeletonProps?.sx : [skeletonProps?.sx])
            ]}
          />
        );
      } else {
        return <Skeleton variant="rounded" height="325px" width="300px" {...skeletonProps} />;
      }
    }

    if (!result) return null;

    if (result.outcome === 'failure' && fetchers[fetcherId].format === 'status') {
      return (
        <Chip
          icon={
            <Tooltip title={result.error}>
              <Icon icon="mdi:information-outline" fontSize="1.25rem" />
            </Tooltip>
          }
          label={t('error')}
          color="error"
          {...chipProps}
        />
      );
    }

    if (result.outcome === 'pending') {
      return (
        <Stack flex={1} sx={{ pt: 2, alignItems: 'center' }} spacing={1}>
          {result.data?.summary && <Typography variant="caption">{result.data.summary}</Typography>}
          <LinearProgress
            variant={result.data?.progress ? 'determinate' : 'indeterminate'}
            value={result.data?.progress * 100}
            sx={{ maxWidth: 500, width: '100%', borderRadius: theme.shape.borderRadius }}
          />
        </Stack>
      );
    }

    if (result.format === 'status') {
      return <StatusChip data={result.data} {...chipProps} />;
    }

    return (
      <Paper
        {...paperProps}
        sx={[
          {
            p: 1,
            overflow: 'hidden',
            flex: 1,
            width: '100%',
            minWidth: '300px'
          },
          ...(Array.isArray(paperProps?.sx) ? paperProps?.sx : [paperProps?.sx])
        ]}
      >
        <Stack
          sx={{
            '& > img': {
              borderRadius: '3px',
              cursor: 'zoom-in',
              transition: theme.transitions.create('border-color', { duration: theme.transitions.duration.shortest }),
              border: '3px solid transparent',
              '&:hover': {
                borderColor: 'primary.main'
              }
            }
          }}
        >
          {result.outcome === 'failure' && (
            <code style={{ color: theme.palette.error.main }}>
              <pre style={{ marginTop: 0, marginBottom: 0 }}>{result.error}</pre>
            </code>
          )}

          <FetcherResultView result={result} fetcherId={fetcherId} {...resultAdditionalProps} />

          <FlexOne />
          <Stack
            direction="row"
            spacing={1}
            {...stackProps}
            sx={[
              {
                py: theme.spacing(0.5),
                display: 'flex',
                alignItems: 'center'
              },
              ...(Array.isArray(stackProps?.sx) ? stackProps?.sx : [stackProps?.sx])
            ]}
          >
            <Iconified icon="ic:baseline-landscape" color="primary" fontSize="small" />
            <Tooltip
              title={
                <Stack spacing={0.5}>
                  <span>
                    {t('type')}: {type}
                  </span>
                  <span>
                    {t('value')}: {value}
                  </span>
                  <span>
                    {t('classification')}: {classification ?? 'N/A'}
                  </span>
                </Stack>
              }
            >
              <Iconified icon="ic:outline-info" fontSize="small" />
            </Tooltip>
            <FlexOne />

            {result.link && (
              <IconButton size="small" component="a" href={result.link}>
                <Iconified icon="ic:baseline-open-in-new" fontSize="small" />
              </IconButton>
            )}
          </Stack>
          <PreviewModal
            {...previewProps}
            fetcherId={fetcherId}
            open={showPreview}
            result={result}
            onClose={() => setShowPreview(false)}
          />
        </Stack>
      </Paper>
    );
  }
);

export default memo(Fetcher);
