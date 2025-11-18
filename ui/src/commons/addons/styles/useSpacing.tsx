import { useTheme } from '@mui/material';
import { useMemo } from 'react';

export default function useSpacing(spacing: number) {
  const theme = useTheme();
  return useMemo(() => theme.spacing(spacing), [spacing, theme]);
}
