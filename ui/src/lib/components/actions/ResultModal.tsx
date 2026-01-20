import { Icon } from '@iconify/react';
import { Button, Divider, LinearProgress, Modal, Paper, Stack, Typography } from '@mui/material';
import JSONViewer from 'lib/components/display/json';
import Markdown from 'lib/components/display/markdown';
import { ClueComponentContext } from 'lib/hooks/ClueComponentContext';
import { useActionResult } from 'lib/hooks/useActionResult';
import type { ActionResult } from 'lib/types/action';
import type { WithActionData } from 'lib/types/WithActionData';
import type { FC } from 'react';
import { memo } from 'react';
import { useContextSelector } from 'use-context-selector';
import ClassificationChip from '../ClassificationChip';
import ErrorBoundary from '../ErrorBoundary';

/**
 * The Annotation Popover is for showing a permanent popover on click with interactivity. For showing data on hover, use Annotation Popper.
 */
const ResultModal: FC<{
  show?: boolean;
  result: WithActionData<ActionResult>;
  onClose?: () => void;
}> = ({ result: _result, onClose, show = false }) => {
  const { t } = useContextSelector(ClueComponentContext, ctx => ctx.i18next);

  const result = useActionResult(_result);

  if (!result) {
    return null;
  }

  return (
    <Modal open={show} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClose={onClose}>
      <Paper sx={{ maxHeight: '80%', maxWidth: '80%', height: '100%', p: 2, minWidth: '750px' }}>
        <ErrorBoundary>
          <Stack spacing={1} height="100%">
            <Stack direction="row" spacing={1} alignItems="center">
              {result.action.action_icon && <Icon height="1.5rem" icon={result.action.action_icon} />}
              <Typography variant="h5">{result.action.name}</Typography>
              {result.action.supported_types && (
                <Typography variant="caption" color="text.secondary">
                  {result.action.supported_types.map(type => type.toUpperCase()).join(', ')}
                </Typography>
              )}
              <div style={{ flex: 1 }} />
              <ClassificationChip size="small" classification={result.action.classification} />
            </Stack>

            <Typography variant="body1">{result.action.summary}</Typography>
            <Divider flexItem />
            {result.done ? (
              <ErrorBoundary>
                {result.format === 'markdown' ? (
                  <Markdown md={result.output} />
                ) : result.format === 'json' ? (
                  <JSONViewer data={result.output} collapse forceCompact />
                ) : (
                  <>
                    <Markdown md={'`' + result.format + '` is not recognized as a format in this application.'} />
                    <JSONViewer data={result} collapse forceCompact />
                  </>
                )}
              </ErrorBoundary>
            ) : (
              <Stack flex={1} sx={{ pt: 2, alignItems: 'center', maxWidth: 500 }} spacing={1}>
                {result.summary && <Typography variant="caption">{result.summary}</Typography>}
                <LinearProgress
                  variant={result.output?.progress ? 'determinate' : 'indeterminate'}
                  value={result.output?.progress * 100}
                  sx={{ width: '100%', borderRadius: theme => theme.shape.borderRadius }}
                />
              </Stack>
            )}

            <div style={{ flex: 1 }} />
            <Stack direction="row" spacing={1}>
              <div style={{ flex: 1 }} />
              {result.link && (
                <Button variant="outlined" component="a" target="_blank" href={result.link}>
                  {t('details.open')}
                </Button>
              )}
              <Button variant="outlined" color="error" onClick={onClose}>
                {t('close')}
              </Button>
            </Stack>
          </Stack>
        </ErrorBoundary>
      </Paper>
    </Modal>
  );
};

export default memo(ResultModal);
