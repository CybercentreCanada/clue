import type { IconProps } from '@iconify/react';
import { Icon } from '@iconify/react';
import { Divider, Stack, Typography, useTheme } from '@mui/material';
import CountBadge from 'lib/components/CountBadge';
import { CluePopupContext } from 'lib/hooks/CluePopupContext';
import useClueActions from 'lib/hooks/useClueActions';
import type { ActionResult } from 'lib/types/action';
import type { Selector } from 'lib/types/lookup';
import type { WithActionData } from 'lib/types/WithActionData';
import groupBy from 'lodash-es/groupBy';
import type { FC } from 'react';
import { memo, useEffect, useMemo, useRef } from 'react';
import { useContextSelector } from 'use-context-selector';

const ResultDetails: FC<{ result: WithActionData<ActionResult> }> = ({ result }) => {
  return (
    <Stack p={1}>
      <Typography variant="body1">{result.action.name}</Typography>
      <Typography variant="caption" color="text.secondary">
        {result.summary}
      </Typography>
    </Stack>
  );
};

const ActionIcon: FC<
  {
    value: Selector;
    counters?: boolean;
    disableTooltip?: boolean;
  } & Omit<IconProps, 'icon'>
> = ({ value, counters = true, disableTooltip = false, ...otherProps }) => {
  const theme = useTheme();

  const showInfo = useContextSelector(CluePopupContext, state => state.showInfo);
  const closeInfo = useContextSelector(CluePopupContext, state => state.closeInfo);

  const successAnchorRef = useRef<HTMLElement>();
  const failureAnchorRef = useRef<HTMLElement>();

  const { getActionResults } = useClueActions();

  const actionResults = useMemo(
    () => getActionResults(value.type, value.value, value.classification),
    [getActionResults, value.classification, value.type, value.value]
  );

  useEffect(() => {
    if (disableTooltip) {
      closeInfo('context', value);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [disableTooltip]);

  const [successes, failures] = useMemo(() => {
    const outcomes = groupBy(actionResults, result => result.outcome);

    return [outcomes.success ?? [], outcomes.failure ?? []];
  }, [actionResults]);

  const successContent = useMemo(() => {
    const entries = successes.map(result => <ResultDetails key={result.actionId} result={result} />);

    return (
      <Stack spacing={1} divider={<Divider flexItem orientation="horizontal" />}>
        {entries}
      </Stack>
    );
  }, [successes]);

  const failureContent = useMemo(() => {
    const entries = failures.map(result => <ResultDetails key={result.summary} result={result} />);

    return (
      <Stack spacing={1} divider={<Divider flexItem orientation="horizontal" />}>
        {entries}
      </Stack>
    );
  }, [failures]);

  if (actionResults?.length < 1) {
    return null;
  }

  return (
    <Stack direction="row" spacing={1}>
      <Divider flexItem orientation="vertical" />
      {successes.length > 0 && (
        <span
          ref={successAnchorRef}
          style={{ display: 'flex' }}
          onMouseOver={
            disableTooltip
              ? undefined
              : () => showInfo('actionResults', successAnchorRef.current, value, { content: successContent })
          }
          onMouseLeave={disableTooltip ? undefined : () => closeInfo('actionResults', value)}
        >
          <CountBadge disabled={!counters} count={actionResults.filter(result => result.outcome === 'success').length}>
            <Icon
              icon="material-symbols:bookmark-check-rounded"
              color={theme.palette.success.main}
              fontSize="1.5em"
              {...otherProps}
            />
          </CountBadge>
        </span>
      )}
      {failures.length > 0 && (
        <span
          ref={failureAnchorRef}
          style={{ display: 'flex' }}
          onMouseOver={
            disableTooltip
              ? undefined
              : () => showInfo('actionResults', failureAnchorRef.current, value, { content: failureContent })
          }
          onMouseLeave={disableTooltip ? undefined : () => closeInfo('actionResults', value)}
        >
          <CountBadge disabled={!counters} count={actionResults.filter(result => result.outcome === 'failure').length}>
            <Icon
              icon="material-symbols:cancel-presentation-rounded"
              color={theme.palette.error.main}
              fontSize="1.5em"
              {...otherProps}
            />
          </CountBadge>
        </span>
      )}
    </Stack>
  );
};

export default memo(ActionIcon);
