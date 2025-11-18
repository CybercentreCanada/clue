import type { ChipProps } from '@mui/material';
import { Chip, Tooltip } from '@mui/material';
import useClueConfig from 'lib/hooks/useClueConfig';
import { getParts, normalizedClassification } from 'lib/utils/classificationParser';
import type { FC } from 'react';
import React, { memo, useMemo } from 'react';

interface EnrichedChipProps {
  classification: string;
}

const THEME_TYPES = ['default', 'primary', 'secondary', 'error', 'info', 'success', 'warning'];

const ClassificationChip: FC<EnrichedChipProps & Exclude<ChipProps, 'label'>> = React.memo(
  ({ classification, ...otherProps }) => {
    const { config } = useClueConfig();

    const parts = useMemo(() => {
      if (!config.c12nDef) {
        return null;
      }

      return getParts(classification, config.c12nDef, 'short', true);
    }, [classification, config.c12nDef]);

    const normalized = useMemo(() => {
      if (!config.c12nDef || !parts) {
        return classification;
      }

      return normalizedClassification(parts, config.c12nDef, 'short', true);
    }, [classification, config.c12nDef, parts]);

    const chipProps = useMemo(() => {
      const definedColor = config.c12nDef?.levels_styles_map[config.c12nDef?.levels_map[parts.lvlIdx]]?.color;

      if (THEME_TYPES.includes(definedColor)) {
        return { color: definedColor };
      }

      if (definedColor) {
        return { sx: { color: definedColor } };
      }

      return { color: 'default' };
    }, [config.c12nDef?.levels_map, config.c12nDef?.levels_styles_map, parts.lvlIdx]);

    return (
      <Tooltip title={classification}>
        <Chip
          variant={otherProps.variant || 'outlined'}
          label={normalized}
          {...chipProps}
          {...otherProps}
          sx={[
            ...(Array.isArray(chipProps.sx) ? chipProps.sx : [chipProps.sx]),
            ...(Array.isArray(otherProps.sx) ? otherProps.sx : [otherProps.sx])
          ]}
        />
      </Tooltip>
    );
  }
);

export default memo(ClassificationChip);
