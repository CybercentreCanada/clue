import { Chip, useMediaQuery, useTheme } from '@mui/material';
import useClueConfig from 'lib/hooks/useClueConfig';
import type { FC } from 'react';
import { useMemo } from 'react';

const Classification: FC = () => {
  const { config } = useClueConfig();
  const theme = useTheme();
  const isSm = useMediaQuery(theme.breakpoints.down('md'));

  const label = useMemo(() => {
    if (isSm) {
      return config.c12nDef?.UNRESTRICTED?.replace(/[a-z]/g, '').replace(/ /g, '') ?? '???';
    } else {
      return config.c12nDef?.UNRESTRICTED ?? 'Unknown';
    }
  }, [config.c12nDef?.UNRESTRICTED, isSm]);

  const color = useMemo(
    () => config.c12nDef?.levels_styles_map?.[label.replace(/\/\/.+/, '')]?.color ?? 'default',
    [config.c12nDef?.levels_styles_map, label]
  );

  return (
    <Chip
      label={config.c12nDef?.levels_map_stl?.[label] ?? label}
      color={color}
      sx={{ mr: 1, fontSize: '.9rem', p: 2, textTransform: 'uppercase' }}
    />
  );
};

export default Classification;
