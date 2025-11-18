import { Box, BoxProps } from '@mui/material';
import { ReactElement } from 'react';

type VSBoxContentProps = Omit<BoxProps, 'children'> & { children: ReactElement };

export default function VSBoxContent({ children, ...boxProps }: VSBoxContentProps) {
  return (
    <Box data-vsbox-content="true" {...boxProps}>
      {children}
    </Box>
  );
}
