import { Box, Link, Typography } from '@mui/material';
import { FeedItem } from 'commons/components/notification';
import * as DOMPurify from 'dompurify';
import React, { FC } from 'react';
import Markdown from 'react-markdown';

export const NotificationItemContent: FC<FeedItem> = React.memo(
  ({ content_html = null, content_text = null, content_md = null }) =>
    content_md ? (
      <Box sx={{ '& *': { margin: 0, marginBottom: 0.5 }, overflow: 'hidden' }}>
        <Markdown components={{ a: props => <Link href={props.href}>{props.children}</Link> }} children={content_md} />
      </Box>
    ) : content_html ? (
      <Typography
        sx={{ '& *': { margin: 0, marginBottom: 0.5 }, overflow: 'hidden' }}
        dangerouslySetInnerHTML={{
          __html: DOMPurify.sanitize(content_html, { USE_PROFILES: { html: true } })
        }}
      />
    ) : content_text ? (
      <Typography
        sx={{ '& *': { margin: 0, marginBottom: 0.5 }, overflow: 'hidden' }}
        variant="body2"
        color="textPrimary"
        children={content_text}
      />
    ) : null
);
