import type { IconProps } from '@iconify/react';
import { Icon } from '@iconify/react';
import { Chip, Divider, Grid, Stack, useTheme } from '@mui/material';
import CountBadge from 'lib/components/CountBadge';
import { CluePopupContext } from 'lib/hooks/CluePopupContext';
import type { Annotation, Selector } from 'lib/types/lookup';
import chain from 'lib/utils/chain';
import groupBy from 'lodash-es/groupBy';
import sortBy from 'lodash-es/sortBy';
import sumBy from 'lodash-es/sumBy';
import type { FC } from 'react';
import { memo, useCallback, useEffect, useMemo, useRef } from 'react';
import { useContextSelector } from 'use-context-selector';

type Opinions = 'benign' | 'suspicious' | 'malicious' | 'obscure';

const OpinionIcon: FC<
  {
    annotations: Annotation[];
    value: Selector;
    counters?: boolean;
    disableTooltip?: boolean;
    ubiquitous?: boolean;
  } & Omit<IconProps, 'icon'>
> = ({ annotations, value, counters = true, disableTooltip = false, ubiquitous = false, ...otherProps }) => {
  const theme = useTheme();
  const showInfo = useContextSelector(CluePopupContext, state => state.showInfo);
  const closeInfo = useContextSelector(CluePopupContext, state => state.closeInfo);

  const anchorRef = useRef<HTMLElement>();

  const opinionAnnotations = useMemo(
    () => annotations.filter(annotation => annotation.type === 'opinion' && annotation.ubiquitous === ubiquitous),
    [annotations, ubiquitous]
  );

  const sortedOpinions = useMemo(
    () =>
      chain(
        Object.entries(groupBy(opinionAnnotations, 'value')).map(([_value, _annotations]) => [
          _value,
          sumBy(_annotations, 'quantity')
        ])
      )
        .sortBy(([__, count]) => count)
        .reverse()
        .value() as [Opinions, number][],
    [opinionAnnotations]
  );

  const icon = useCallback(
    (_opinion: string) =>
      _opinion === 'benign'
        ? 'mdi:shield-check'
        : _opinion === 'suspicious'
          ? 'mdi:warning-outline'
          : _opinion === 'obscure'
            ? 'bi:eye-slash-fill'
            : 'mdi:warning-decagram',
    []
  );

  useEffect(() => {
    if (disableTooltip) {
      closeInfo('opinion', value);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [disableTooltip]);

  const tooltipContent = useMemo(
    () => (
      <Stack spacing={1} onClick={e => e.stopPropagation()}>
        {opinionAnnotations.length > 1 && (
          <>
            <Stack direction="row">
              {sortedOpinions.map(([type, count]) => (
                <Chip
                  key={type}
                  size="small"
                  variant="outlined"
                  label={`${type}: ${count}`}
                  icon={<Icon icon={icon(type as string)} />}
                  sx={{ textTransform: 'capitalize' }}
                  color={
                    {
                      benign: 'success' as const,
                      suspicious: 'warning' as const,
                      obscure: 'error' as const,
                      malicious: 'error' as const
                    }[type] as any
                  }
                />
              ))}
            </Stack>
            <Divider orientation="horizontal" flexItem />
          </>
        )}
        <Grid
          sx={{
            mt: opinionAnnotations.length < 2 && `${theme.spacing(-0.5)} !important`,
            ml: `${theme.spacing(-0.5)} !important`
          }}
          container
          spacing={0.5}
          maxWidth="500px"
        >
          {sortBy(opinionAnnotations, 'value').map(annotation => (
            <Grid item key={(annotation.analytic ?? annotation.author) + annotation.value}>
              <Chip
                size="small"
                variant="outlined"
                label={
                  (annotation.analytic ?? annotation.author) +
                  (annotation.quantity > 1 ? ` (x${annotation.quantity})` : '')
                }
                icon={<Icon icon={icon(annotation.value as string)} />}
                color={
                  {
                    benign: 'success' as const,
                    suspicious: 'warning' as const,
                    obscure: 'error' as const,
                    malicious: 'error' as const
                  }[annotation.value] as any
                }
              />
            </Grid>
          ))}
        </Grid>
      </Stack>
    ),
    [icon, opinionAnnotations, sortedOpinions, theme]
  );

  if (opinionAnnotations?.length < 1) {
    return null;
  }

  return (
    <span
      ref={anchorRef}
      style={{ display: 'flex' }}
      onMouseOver={
        disableTooltip ? undefined : () => showInfo('assessment', anchorRef.current, value, { content: tooltipContent })
      }
      onMouseLeave={disableTooltip ? undefined : () => closeInfo('assessment', value)}
    >
      <CountBadge disabled={!counters} count={sortedOpinions[0][1]}>
        <Icon
          fontSize="1.25em"
          {...otherProps}
          icon={icon(sortedOpinions[0][0])}
          color={
            {
              benign: theme.palette.success.light,
              suspicious: theme.palette.warning.light,
              obscure: theme.palette.error.light,
              malicious: theme.palette.error.light
            }[sortedOpinions[0][0]] as any
          }
          style={{
            zIndex: 2,
            ...(otherProps.style ?? {})
          }}
        />
      </CountBadge>
    </span>
  );
};

export default memo(OpinionIcon);
