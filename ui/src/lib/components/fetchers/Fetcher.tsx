/* eslint-disable no-console */
import { Icon } from '@iconify/react';
import type { ChipProps, ModalProps, PaperProps, SkeletonProps, StackProps } from '@mui/material';
import { Box, Chip, IconButton, Paper, Skeleton, Stack, Tooltip, useTheme } from '@mui/material';
import FlexOne from 'commons/addons/flexers/FlexOne';
import Iconified from 'lib/components/display/icons/Iconified';
import JSONViewer from 'lib/components/display/json';
import { ClueComponentContext } from 'lib/hooks/ClueComponentContext';
import { useClueFetcherSelector } from 'lib/hooks/selectors';
import type { FetcherResult } from 'lib/types/fetcher';
import type { Selector } from 'lib/types/lookup';
import type { FC } from 'react';
import React, { memo, useEffect, useState } from 'react';
import { useContextSelector } from 'use-context-selector';
import Graph from '../display/graph';
import Markdown from '../display/markdown';
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
    const fetchCompleted = useClueFetcherSelector(ctx => ctx.fetchCompleted);

    const { t } = useContextSelector(ClueComponentContext, ctx => ctx?.i18next);

    const [result, setResult] = useState<FetcherResult>(null);
    const [loading, setLoading] = useState(true);
    const [showPreview, setShowPreview] = useState(false);

    useEffect(() => {
      (async () => {
        try {
          setLoading(true);
          setResult(
            fetcherId in fetchers
              ? await fetchSelector(fetcherId, { type, value, classification })
              : {
                  outcome: 'failure',
                  error:
                    'Fetcher ID does not correspond to a registered fetcher. Do you have the correct access level?',
                  format: 'json',
                  data: null,
                  link: null
                }
          );
        } finally {
          setLoading(false);
        }
      })();
    }, [classification, fetchSelector, fetcherId, type, value]);

    if (fetchCompleted) {
      if (!fetcherId) {
        console.warn('Missing fetcher Id. Component will not render.');
        return null;
      } else if (!fetcherId.includes('.')) {
        console.warn(
          "Invalid fetcher id. Must be in the format '<plugin_id>.<fetcher_id>'. Component will not render."
        );
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

    if (result?.outcome === 'failure' && fetchers[fetcherId]?.format === 'status') {
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

    if (result?.format === 'status') {
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
          {result?.outcome === 'failure' && (
            <code style={{ color: theme.palette.error.main }}>
              <pre style={{ marginTop: 0, marginBottom: 0 }}>{result.error}</pre>
            </code>
          )}
          {result?.format === 'markdown' && <Markdown md={result.data} />}
          {result?.format === 'image' && (
            <img src={result.data.image} alt={result.data.alt} {...imageProps} onClick={() => setShowPreview(true)} />
          )}
          {result?.format === 'json' && (
            <Box sx={{ '.react-json-view': { backgroundColor: 'transparent !important' } }}>
              <JSONViewer data={result.data} />
            </Box>
          )}
          {result?.format === 'graph' && <Graph graph={result.data} sx={{ minHeight: '600px' }} />}
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

            {result?.link && (
              <IconButton size="small" component="a" href={result.link}>
                <Iconified icon="ic:baseline-open-in-new" fontSize="small" />
              </IconButton>
            )}
          </Stack>
          <PreviewModal {...previewProps} open={showPreview} result={result} onClose={() => setShowPreview(false)} />
        </Stack>
      </Paper>
    );
  }
);

export default memo(Fetcher);
