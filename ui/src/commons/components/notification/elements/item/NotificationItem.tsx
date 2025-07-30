import { useTheme } from '@mui/material';
import { FC, memo } from 'react';
import { FeedItem } from '../..';
import { NotificationItemAuthor } from './NotificationItemAuthor';
import { NotificationItemContent } from './NotificationItemContent';
import { NotificationItemDate } from './NotificationItemDate';
import { NotificationItemImage } from './NotificationItemImage';
import { NotificationItemTag } from './NotificationItemTag';
import { NotificationItemTitle } from './NotificationItemTitle';

export const NotificationItem: FC<{ item?: FeedItem }> = memo(({ item = null }) => {
  const theme = useTheme();

  return !item ? null : (
    <div
      style={{
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start'
      }}
    >
      <NotificationItemDate {...item} />
      <NotificationItemTitle {...item} />
      <NotificationItemContent {...item} />
      <NotificationItemImage {...item} />
      <div
        style={{
          width: '100%',
          display: 'flex',
          flexDirection: 'row',
          alignItems: 'center',
          marginTop: theme.spacing(1)
        }}
      >
        {item?.tags && item?.tags.map(tag => <NotificationItemTag key={`${tag}`} tag={tag} />)}
        <div style={{ flex: 1 }} />
        {item?.authors &&
          item?.authors.map(author => <NotificationItemAuthor key={`${author?.name}`} author={author} />)}
      </div>
    </div>
  );
});
