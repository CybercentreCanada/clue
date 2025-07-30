import { Box } from '@mui/material';
import { memo } from 'react';
import { PageProps } from './hooks/usePageProps';
import PageContent from './PageContent';

type PageCenterProps = PageProps & {
  children: React.ReactNode;
  maxWidth?: string;
  textAlign?: string;
};

const PageCenter = ({
  children,
  height,
  width = '95%',
  maxWidth = '1200px',
  textAlign = 'center',
  ...props
}: PageCenterProps) => {
  return (
    <Box
      component="div"
      height={height}
      width={width}
      maxWidth={maxWidth}
      sx={theme => ({
        height,
        width,
        textAlign,
        display: 'flex',
        flexDirection: 'column',
        margin: '0 auto 0 auto',
        maxWidth,
        [theme.breakpoints.down('sm')]: {
          maxWidth: '100%'
        }
      })}
    >
      <PageContent {...props} height="100%">
        {children}
      </PageContent>
    </Box>
  );
};

export default memo(PageCenter);
