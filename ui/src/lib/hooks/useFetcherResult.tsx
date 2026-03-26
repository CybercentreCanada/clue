import type { ActionResult } from 'lib/types/action';
import type { WithActionData } from 'lib/types/WithActionData';
import { useEffect, useMemo, useRef, useState } from 'react';
import useClueActions from './useClueActions';

export const useActionResult = (resultWithData: WithActionData<ActionResult>, interval = 2000) => {
  const [result, setResult] = useState<ActionResult>(resultWithData);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const { getActionStatus } = useClueActions();

  const taskId = useMemo(() => resultWithData?.task_id, [resultWithData?.task_id]);

  const actionId = useMemo(() => resultWithData?.actionId, [resultWithData?.actionId]);

  useEffect(() => {
    if (resultWithData?.outcome !== 'pending' || !taskId) return;

    let cancelled = false;

    const poll = async () => {
      const res = await getActionStatus(actionId, taskId);

      if (!res) {
        setResult({ outcome: 'failure', done: true });
      } else if (res.outcome === 'success' || res.outcome === 'failure') {
        setResult({ ...res, done: true });
      } else {
        if (cancelled) return;
        setResult({ ...res });
        timeoutRef.current = setTimeout(poll, interval);
      }
    };

    poll();

    return () => {
      cancelled = true;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [actionId, getActionStatus, interval, resultWithData?.outcome, taskId]);

  useEffect(() => {
    setResult(resultWithData);
  }, [resultWithData]);

  return useMemo(
    () => (resultWithData || result ? { ...resultWithData, ...result } : undefined),
    [resultWithData, result]
  );
};
