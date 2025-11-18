import { darken, lighten } from '@mui/material';
import useAppTheme from 'commons/components/app/hooks/useAppTheme';
import { useCallback } from 'react';

export default function useMyUtils() {
  const { isDark } = useAppTheme();

  return {
    shiftColor: useCallback(
      (color: string, coefficient: number) => (isDark ? darken : lighten)(color, coefficient),
      [isDark]
    )
  };
}
