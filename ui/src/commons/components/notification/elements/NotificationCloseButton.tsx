import CloseOutlinedIcon from '@mui/icons-material/CloseOutlined';
import { IconButton } from '@mui/material';
import { FC, memo } from 'react';
import { NotificationProps } from './NotificationContainer';

export const NotificationCloseButton: FC<NotificationProps> = memo(
  ({ drawer = false, onDrawerOpen = () => null, onDrawerClose = () => null }) => (
    <div>
      <IconButton
        onClick={() => (drawer ? onDrawerClose() : onDrawerOpen())}
        children={<CloseOutlinedIcon fontSize="medium" />}
        size="large"
      />
    </div>
  )
);
