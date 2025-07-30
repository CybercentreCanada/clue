import { Box, BoxProps, useTheme } from '@mui/material';
import { ReactElement, useEffect, useRef } from 'react';
import { useResizeDetector } from 'react-resize-detector';
import useVsBox from './hooks/useVsBox';

type VSBoxHeaderProps = Omit<BoxProps, 'children'> & { children: ReactElement | ReactElement[] };

export default function VSBoxHeader({ children, ...boxProps }: VSBoxHeaderProps) {
  const theme = useTheme();
  const heightRef = useRef<number>();
  const { height, ref } = useResizeDetector({ handleWidth: false });
  const { state, setState } = useVsBox();

  useEffect(() => {
    if (height !== heightRef.current) {
      setState({ ...state, scrollTop: state.top + height });
      heightRef.current = height;
    }
  }, [height, state, setState]);

  return (
    <Box
      {...boxProps}
      ref={ref}
      data-vsbox-header="true"
      position="sticky"
      top={state.top}
      sx={{
        backgroundColor: theme.palette.background.default,
        zIndex: theme.zIndex.appBar - 1,
        ...(boxProps.sx && { ...boxProps.sx })
      }}
    >
      {children}
    </Box>
  );
}
