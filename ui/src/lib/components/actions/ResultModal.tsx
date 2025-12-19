import { Icon } from '@iconify/react';
import { Button, CircularProgress, Divider, Modal, Paper, Stack, Typography } from '@mui/material';
import JSONViewer from 'lib/components/display/json';
import Markdown from 'lib/components/display/markdown';
import { ClueComponentContext } from 'lib/hooks/ClueComponentContext';
import type { ActionResult } from 'lib/types/action';
import type { WithActionData } from 'lib/types/WithActionData';
import type { FC } from 'react';
import { memo, useEffect, useMemo, useRef, useState } from 'react';
import { useContextSelector } from 'use-context-selector';
import ClassificationChip from '../ClassificationChip';
import ErrorBoundary from '../ErrorBoundary';
import api from 'api';


export const useActionResult = (resultWithData: WithActionData<ActionResult>, interval = 1000) => {
  const [result, setResult] = useState<ActionResult>(resultWithData);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const taskId = useMemo(() => resultWithData?.output?.task_id, [resultWithData?.output?.task_id]);

  const actionId = useMemo(() => resultWithData?.actionId, [resultWithData?.actionId]);

  useEffect(() => {
    if (!taskId) return;

    let cancelled = false;

    const poll = async () => {

      const res = await api.actions.post(
        actionId,
        [{ type: 'task_id', value: taskId }],
        {},
        {},
        {},
        {}
      );

      if (res.outcome === "success" || res.outcome === "failure") {
        setResult({ ...res, done: true });
      } else {
        if (cancelled) return;
        timeoutRef.current = setTimeout(poll, interval);
      }

    };

    poll();

    return () => {
      cancelled = true;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [taskId, interval, actionId]);

  useEffect(() => {
    setResult(resultWithData);
  }, [resultWithData]);

  return useMemo(() => resultWithData || result ? ({ ...resultWithData, ...result }) : undefined, [resultWithData, result]);

};

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
            {result.done ? <ErrorBoundary>
              {result.format === 'markdown' && <Markdown md={result.output} />}
              {result.format === 'json' && <JSONViewer data={result.output} collapse forceCompact />}
            </ErrorBoundary> : <CircularProgress />}

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
