import type { ActionResult } from 'lib/types/action';
import type { WithActionData } from 'lib/types/WithActionData';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useContextSelector } from 'use-context-selector';
import { ClueComponentContext } from './ClueComponentContext';
import { useClueActionsSelector } from './selectors';

export const useActionResult = (resultWithData: WithActionData<ActionResult>, interval = 2000) => {
  const [result, setResult] = useState<ActionResult>(resultWithData);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const { t } = useContextSelector(ClueComponentContext, ctx => ctx.i18next);
  const getActionStatus = useClueActionsSelector(ctx => ctx.getActionStatus);

  const taskId = useMemo(() => resultWithData?.task_id, [resultWithData?.task_id]);

  const actionId = useMemo(() => resultWithData?.actionId, [resultWithData?.actionId]);

  useEffect(() => {
    if (resultWithData?.outcome !== 'pending' || !taskId) {
      return;
    }

    let cancelled = false;
    const poll = async () => {
      const res = await getActionStatus(actionId, taskId);

      if (cancelled) {
        return;
      }

      let _result: ActionResult;
      if (!res) {
        _result = { outcome: 'failure', summary: t('error.unexpected'), done: true };
      } else if (res.outcome === 'success' || res.outcome === 'failure') {
        _result = { ...res, done: true };
      } else {
        _result = res;
      }

      setResult(_result);
      if (_result.done) {
        resultWithData?.onComplete?.({ ...resultWithData, ..._result });
      } else {
        timeoutRef.current = setTimeout(poll, interval);
      }
    };

    poll();

    return () => {
      cancelled = true;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [actionId, getActionStatus, interval, resultWithData, resultWithData?.outcome, t, taskId]);

  useEffect(() => {
    setResult(resultWithData);
  }, [resultWithData]);

  return useMemo(
    () => (resultWithData || result ? { ...resultWithData, ...result } : undefined),
    [resultWithData, result]
  );
};
