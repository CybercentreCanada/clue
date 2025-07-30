import NotificationsActiveOutlinedIcon from '@mui/icons-material/NotificationsActiveOutlined';
import NotificationsNoneOutlinedIcon from '@mui/icons-material/NotificationsNoneOutlined';
import { Badge, IconButton, Tooltip } from '@mui/material';
import { FC, memo } from 'react';
import { useTranslation } from 'react-i18next';

type TopNavButtonProps = {
  newItems?: number;
  drawer?: boolean;
  onDrawerOpen: () => void;
  onDrawerClose: () => void;
};

export const NotificationTopNavButton: FC<TopNavButtonProps> = memo(
  ({ newItems = 0, drawer = false, onDrawerOpen = () => null, onDrawerClose = () => null }) => {
    const { t } = useTranslation();

    return (
      <Tooltip title={t('notification.title')}>
        <IconButton color="inherit" onClick={() => (drawer ? onDrawerClose() : onDrawerOpen())} size="large">
          <Badge badgeContent={newItems} color="info" max={99}>
            {newItems > 0 ? <NotificationsActiveOutlinedIcon /> : <NotificationsNoneOutlinedIcon />}
          </Badge>
        </IconButton>
      </Tooltip>
    );
  }
);
