import { Grid, Stack } from '@mui/material';
import PageCenter from 'commons/components/pages/PageCenter';
import type { ClueUser } from 'models/entities/ClueUser';
import type { FC, PropsWithChildren } from 'react';

const UserPageWrapper: FC<PropsWithChildren<{ user: ClueUser }>> = ({ children }) => (
  <PageCenter textAlign="left" mt={6}>
    <Grid container spacing={2} justifyContent="center">
      <Grid item sm={12} md={9}>
        <Stack direction="column" spacing={2}>
          {children}
        </Stack>
      </Grid>
    </Grid>
  </PageCenter>
);

export default UserPageWrapper;
