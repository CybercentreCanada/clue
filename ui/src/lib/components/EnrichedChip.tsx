import type { ChipProps } from '@mui/material';
import { Box, Chip, CircularProgress, Stack, Tooltip } from '@mui/material';
import Iconified from 'lib/components/display/icons/Iconified';
import { ClueComponentContext } from 'lib/hooks/ClueComponentContext';
import { ClueGroupContext } from 'lib/hooks/ClueGroupContext';
import type { ShowInfoOptions } from 'lib/hooks/CluePopupContext';
import { CluePopupContext } from 'lib/hooks/CluePopupContext';
import { useClueEnrichSelector } from 'lib/hooks/selectors';
import useAnnotations from 'lib/hooks/useAnnotations';
import ActionIcon from 'lib/icons/Action';
import AssessmentIcon from 'lib/icons/Assessment';
import ContextIcon from 'lib/icons/Context';
import OpinionIcon from 'lib/icons/Opinion';
import FrequencyText from 'lib/text/Frequency';
import type EnrichmentProps from 'lib/types/EnrichmentProps';
import type { FC } from 'react';
import React, { memo, useCallback, useEffect, useMemo, useRef } from 'react';
import { useContextSelector } from 'use-context-selector';

const EnrichedChip: FC<EnrichmentProps & ChipProps> = React.memo(
  ({
    type: _type,
    value,
    classification: _classification,
    contextIcon = false,
    counters = false,
    hideDetails = false,
    hideLoading = false,
    forceDetails = false,
    setForceDetails = null,
    useDetailsIcon = false,
    skipEnrichment = false,
    slotProps = {},
    ...otherProps
  }) => {
    const { t } = useContextSelector(ClueComponentContext, ctx => ctx.i18next);
    const anchorRef = useRef<HTMLDivElement>();

    const groupType = useContextSelector(ClueGroupContext, ctx => ctx?.type);
    const defaultClassification = useClueEnrichSelector(ctx => ctx.defaultClassification);

    const type = useMemo(() => _type ?? groupType, [_type, groupType]);
    const classification = useMemo(
      () => _classification ?? defaultClassification,
      [_classification, defaultClassification]
    );

    if (!type) {
      throw new Error('Type was not provided as a prop, and component is not used in a group context.');
    }

    const [annotations, loading] = useAnnotations(type, value, classification, { skipEnrichment });

    const showInfo = useContextSelector(CluePopupContext, ctx => ctx.showInfo);
    const closeInfo = useContextSelector(CluePopupContext, ctx => ctx.closeInfo);

    const buildOptions = useCallback(() => {
      const options: ShowInfoOptions = {};
      if (setForceDetails) {
        options.onClose = () => setForceDetails(false);
      }

      if (slotProps?.popover) {
        options.popoverProps = slotProps.popover;
      }

      return options;
    }, [setForceDetails, slotProps.popover]);

    const clicker = useMemo(
      () =>
        !hideDetails || useDetailsIcon
          ? (e: React.MouseEvent<HTMLDivElement, MouseEvent>) => {
              showInfo('details', anchorRef.current, { type, value, classification }, buildOptions());
              otherProps.onClick?.(e);
              e.stopPropagation();
              e.preventDefault();
            }
          : otherProps.onClick,
      // eslint-disable-next-line react-hooks/exhaustive-deps
      [loading, hideDetails, useDetailsIcon, otherProps, type, value, classification]
    );

    useEffect(() => {
      if (forceDetails) {
        showInfo('details', anchorRef.current, { type, value, classification }, buildOptions());
      } else {
        closeInfo('details', {
          type,
          value,
          classification
        });
      }
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [classification, forceDetails, type, value]);

    return (
      <Chip
        {...otherProps}
        ref={anchorRef}
        variant={otherProps.variant || 'outlined'}
        sx={{
          height: otherProps.size !== 'small' ? '40px' : 'unset',
          '& .MuiChip-label': { overflow: 'visible' },
          ...(otherProps.sx ?? {})
        }}
        label={
          <Stack direction="row" spacing={1} alignItems="center">
            <AssessmentIcon
              ubiquitous
              value={{ type, value, classification }}
              annotations={annotations}
              counters={counters}
              disableTooltip={forceDetails}
              style={{ flexShrink: 0 }}
            />
            <OpinionIcon
              ubiquitous
              value={{ type, value, classification }}
              annotations={annotations}
              counters={counters}
              disableTooltip={forceDetails}
              style={{ flexShrink: 0 }}
            />
            <ContextIcon
              ubiquitous
              value={{ type, value, classification }}
              annotations={annotations}
              counters={counters}
              showExtraIcon={contextIcon}
              disableTooltip={forceDetails}
              style={{ flexShrink: 0 }}
            />
            {otherProps.label ?? <FrequencyText fontSize="inherit" annotations={annotations} value={value} />}
            <AssessmentIcon
              value={{ type, value, classification }}
              annotations={annotations}
              counters={counters}
              disableTooltip={forceDetails}
              style={{ flexShrink: 0 }}
            />
            <OpinionIcon
              value={{ type, value, classification }}
              annotations={annotations}
              counters={counters}
              disableTooltip={forceDetails}
              style={{ flexShrink: 0 }}
            />
            <ContextIcon
              value={{ type, value, classification }}
              annotations={annotations}
              counters={counters}
              showExtraIcon={contextIcon}
              disableTooltip={forceDetails}
              style={{ flexShrink: 0 }}
            />
            <ActionIcon counters={counters} value={{ type, value, classification }} disableTooltip={forceDetails} />
            {loading && !hideLoading && <CircularProgress color="primary" size={16} />}
          </Stack>
        }
        onClick={!useDetailsIcon ? clicker : undefined}
        onDelete={!loading && useDetailsIcon ? clicker : undefined}
        deleteIcon={
          useDetailsIcon ? (
            <Tooltip title={t('details.open')}>
              <Box component="span" sx={{ pr: 1 }}>
                <Iconified icon="ic:outline-info" />
              </Box>
            </Tooltip>
          ) : null
        }
      />
    );
  }
);

export default memo(EnrichedChip);
