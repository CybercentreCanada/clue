import { Chip, Skeleton, Typography, useTheme } from '@mui/material';
import { FC, memo } from 'react';

export const NotificationSkeleton: FC = memo(() => {
  const theme = useTheme();
  return (
    <div style={{ width: '100%' }}>
      <Typography variant="caption" children={<Skeleton width="30%" />} />
      <Typography variant="h6" children={<Skeleton width="50%" />} />
      <div style={{ marginTop: theme.spacing(0.25), marginBottom: theme.spacing(1) }}>
        <Typography variant="body2" children={<Skeleton />} />
        <Typography variant="body2" children={<Skeleton />} />
        <Typography variant="body2" children={<Skeleton />} />
      </div>
      <div
        style={{
          width: '100%',
          display: 'flex',
          flexDirection: 'row',
          alignItems: 'center'
        }}
      >
        <Chip
          size="small"
          variant="outlined"
          label={<Skeleton width="30px" />}
          style={{ margin: theme.spacing(0.25) }}
        />
        <Chip
          size="small"
          variant="outlined"
          label={<Skeleton width="30px" />}
          style={{ margin: theme.spacing(0.25) }}
        />
        <div style={{ flex: 1 }} />

        <Skeleton variant="circular" width={25} height={25} style={{ margin: theme.spacing(0.25) }} />
        <Typography variant="caption" children={<Skeleton width={50} />} style={{ margin: theme.spacing(0.25) }} />

        <Skeleton variant="circular" width={25} height={25} style={{ margin: theme.spacing(0.25) }} />
        <Typography variant="caption" children={<Skeleton width={50} />} style={{ margin: theme.spacing(0.25) }} />
      </div>
    </div>
  );
});
