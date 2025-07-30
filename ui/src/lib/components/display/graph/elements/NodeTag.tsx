import { Stack, Tooltip, Typography } from '@mui/material';
import FlexOne from 'commons/addons/flexers/FlexOne';
import type { FC, PropsWithChildren } from 'react';
import Iconified from '../../icons/Iconified';

interface TagOptions {
  nodeId: string;
  label?: string;
  type?: 'header' | 'content';
}

const NodeTag: FC<PropsWithChildren<TagOptions>> = ({ nodeId, label = nodeId, type = 'content', children }) => {
  return (
    <Stack direction="row" spacing={1} alignItems="center" pr={1}>
      {type === 'header' ? (
        <Stack direction="row" spacing={1} alignItems="center" sx={{ overflow: 'hidden' }}>
          <Typography variant="body1" sx={{ wordWrap: 'break-all' }}>
            {label.replace(' (TRUNCATED)', '')}
          </Typography>
          {label.includes('TRUNCATED') && (
            <Tooltip title="Field is truncated.">
              <Iconified icon="ic:baseline-content-cut" fontSize="small" style={{ fontSize: '0.9em' }} />
            </Tooltip>
          )}
        </Stack>
      ) : (
        label
      )}
      <FlexOne />
      {/* <IconButton size="small">
        <TimelineIcon fontSize={type === 'header' ? 'medium' : 'small'} />
      </IconButton> */}
      {children}
    </Stack>
  );
};

export default NodeTag;
