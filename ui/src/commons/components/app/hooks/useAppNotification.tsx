import { useContext } from 'react';
import { AppNotificationServiceContext } from '../providers/AppNotificationProvider';

//
export default function useAppNotification() {
  return useContext(AppNotificationServiceContext);
}
