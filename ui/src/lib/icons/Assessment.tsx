import type { IconProps } from '@iconify/react';
import { Icon } from '@iconify/react';
import { Chip, Divider, Grid, Stack, Tooltip, useTheme } from '@mui/material';
import CountBadge from 'lib/components/CountBadge';
import { CluePopupContext } from 'lib/hooks/CluePopupContext';
import type { Annotation, Selector } from 'lib/types/lookup';
import groupBy from 'lodash-es/groupBy';
import last from 'lodash-es/last';
import maxBy from 'lodash-es/maxBy';
import sortBy from 'lodash-es/sortBy';
import sumBy from 'lodash-es/sumBy';
import type { FC } from 'react';
import { memo, useEffect, useMemo, useRef, useState } from 'react';
import { useContextSelector } from 'use-context-selector';

type Assessments =
  | 'ambiguous'
  | 'security'
  | 'development'
  | 'false-positive'
  | 'legitimate'
  | 'trivial'
  | 'recon'
  | 'attempt'
  | 'compromise'
  | 'mitigated';

const AssessmentIcon: FC<
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

  const [showTooltip, setShowTooltip] = useState(false);

  const assessmentAnnotations = useMemo(
    () => annotations.filter(annotation => annotation?.type === 'assessment' && annotation?.ubiquitous === ubiquitous),
    [annotations, ubiquitous]
  );

  const sortedAssessments = useMemo(
    () =>
      Object.entries(groupBy(assessmentAnnotations, 'value')).map(([_value, _annotations]) => [
        _value,
        sumBy(_annotations, 'quantity')
      ]),
    [assessmentAnnotations]
  );

  const popularAssessment = useMemo(() => maxBy(sortedAssessments, last) as [Assessments, number], [sortedAssessments]);

  useEffect(() => {
    if (disableTooltip) {
      setShowTooltip(false);
    }
  }, [disableTooltip]);

  if (assessmentAnnotations?.length < 1) {
    return null;
  }

  const tooltipProps = {
    tooltip: {
      sx: {
        maxWidth: '500px',
        backgroundColor: theme.palette.background.paper,
        border: `thin solid ${theme.palette.divider}`,
        p: 1,
        boxShadow: theme.shadows[2]
      }
    }
  };

  const tooltipContent = (
    <Stack spacing={1} onClick={e => e.stopPropagation()}>
      {assessmentAnnotations.length > 1 && (
        <>
          <Stack direction="row">
            {sortedAssessments.map(([type, count]) => (
              <Chip
                key={type}
                size="small"
                variant="outlined"
                label={`${type}: ${count}`}
                icon={
                  <Icon
                    icon={
                      ['trivial', 'recon', 'attempt', 'compromise', 'mitigated'].includes(type as string)
                        ? 'healthicons:hazardous'
                        : 'fluent-mdl2:ribbon-solid'
                    }
                  />
                }
                color={
                  ['trivial', 'recon', 'attempt', 'compromise', 'mitigated'].includes(type as string)
                    ? 'error'
                    : 'success'
                }
              />
            ))}
          </Stack>
          <Divider orientation="horizontal" flexItem />
        </>
      )}
      <Grid
        sx={{
          mt: assessmentAnnotations.length < 2 && `${theme.spacing(-0.5)} !important`,
          ml: `${theme.spacing(-0.5)} !important`
        }}
        container
        spacing={0.5}
        maxWidth="500px"
      >
        {sortBy(assessmentAnnotations, 'value').map(annotation => (
          <Grid item key={annotation.analytic + annotation.value}>
            <Chip
              size="small"
              variant="outlined"
              label={annotation.analytic + (annotation.quantity > 1 ? ` (x${annotation.quantity})` : '')}
              icon={
                <Icon
                  icon={
                    ['trivial', 'recon', 'attempt', 'compromise', 'mitigated'].includes(annotation.value as string)
                      ? 'healthicons:hazardous'
                      : 'fluent-mdl2:ribbon-solid'
                  }
                />
              }
              color={
                ['trivial', 'recon', 'attempt', 'compromise', 'mitigated'].includes(annotation.value as string)
                  ? 'error'
                  : 'success'
              }
            />
          </Grid>
        ))}
      </Grid>
    </Stack>
  );

  if (['trivial', 'recon', 'attempt', 'compromise', 'mitigated'].includes(popularAssessment[0])) {
    return (
      <span
        ref={anchorRef}
        style={{ display: 'flex' }}
        onMouseOver={
          disableTooltip
            ? undefined
            : () => showInfo('assessment', anchorRef.current, value, { content: tooltipContent })
        }
        onMouseLeave={disableTooltip ? undefined : () => closeInfo('assessment', value)}
      >
        <CountBadge disabled={!counters} color="error" count={popularAssessment[1]}>
          <Icon fontSize="1.5em" {...otherProps} icon="healthicons:hazardous" color={theme.palette.error.main} />
        </CountBadge>
      </span>
    );
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
      <Tooltip disableInteractive componentsProps={tooltipProps} open={showTooltip} title={tooltipContent}>
        <CountBadge disabled={!counters} count={popularAssessment[1]}>
          <Icon fontSize="1.5em" {...otherProps} icon="fluent-mdl2:ribbon-solid" color={theme.palette.success.main} />
        </CountBadge>
      </Tooltip>
    </span>
  );
};

export default memo(AssessmentIcon);
