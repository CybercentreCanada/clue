import { Stack, Typography } from '@mui/material';
import { ClueDatabaseContext } from 'lib/hooks/ClueDatabaseContext';
import { useClueComponentSelector, useClueEnrichSelector } from 'lib/hooks/selectors';
import type { FC } from 'react';
import { useContext, useEffect, useState } from 'react';

const QueryStatus: FC = () => {
  const { t } = useClueComponentSelector(ctx => ctx.i18next);
  const database = useContext(ClueDatabaseContext);
  const ready = useClueEnrichSelector(ctx => ctx.ready);

  const [pendingCount, setPendingCount] = useState(0);
  const [inProgressCount, setInProgressCount] = useState(0);
  const [completeCount, setCompleteCount] = useState(0);

  useEffect(() => {
    // Fetch and update annotations in real-time using RxDB observables
    if (!ready) {
      return;
    }

    const observables = [
      database.status.count({ selector: { status: 'pending' } }).$.subscribe(setPendingCount),
      database.status.count({ selector: { status: 'in-progress' } }).$.subscribe(setInProgressCount),
      database.status.count({ selector: { status: 'complete' } }).$.subscribe(setCompleteCount)
    ];

    // Cleanup subscription to prevent memory leaks
    return () => {
      try {
        observables.forEach(_observable => _observable.unsubscribe());
      } catch (e) {
        // eslint-disable-next-line no-console
        console.warn(e);
      }
    };
  }, [database, ready]);

  if (pendingCount + inProgressCount + completeCount < 1) {
    return null;
  }

  return (
    <Stack
      spacing={1}
      sx={theme => ({
        border: `thin solid ${theme.palette.divider}`,
        borderRadius: theme.spacing(0.5),
        mx: 1,
        p: 1
      })}
    >
      <Typography sx={{ fontFamily: 'monospace' }}>
        {t('query.status.pending')}: {pendingCount}
      </Typography>
      <Typography sx={{ fontFamily: 'monospace' }}>
        {t('query.status.inprogress')}: {inProgressCount}
      </Typography>
      <Typography sx={{ fontFamily: 'monospace' }}>
        {t('query.status.complete')}: {completeCount}
      </Typography>
    </Stack>
  );
};

export default QueryStatus;
