import { Box } from '@mui/material';
import BuilderPage from 'components/builder/BuilderPage';
import type { FC } from 'react';

const Builder: FC = () => {
  return (
    <Box sx={theme => ({ height: `calc(100vh - ${theme.spacing(8)})` })}>
      <BuilderPage />
    </Box>
  );
};

export default Builder;
