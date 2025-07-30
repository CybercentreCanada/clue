import { Notification } from 'commons/components/notification';
import { FC } from 'react';
import useAppNotification from '../app/hooks/useAppNotification';

export const Notifications: FC = () => {
  const { service, state } = useAppNotification();

  return (
    <Notification
      urls={service.feedUrls || state.urls}
      notificationItem={service.notificationRenderer}
      maxDrawerWidth="800px"
      openIfNew
    />
  );
};
