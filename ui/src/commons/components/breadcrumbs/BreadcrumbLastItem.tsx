import { Tooltip, Typography } from '@mui/material';
import useAppSitemap, { BreadcrumbItem } from 'commons/components/app/hooks/useAppSitemap';
import BreadcrumbIcon from 'commons/components/breadcrumbs/BreadcrumbIcon';
import * as React from 'react';

type BreadcrumbLastItemProps = {
  textOnly?: boolean;
  item: BreadcrumbItem;
};

const BreadcrumbLastItem: React.FC<BreadcrumbLastItemProps> = ({ item, textOnly }) => {
  const { route, matcher } = item;
  const { getTitle: resolveTitle } = useAppSitemap();
  const url = matcher ? matcher.pathname : route.path;

  return (
    <Typography
      key={`bcrumb-${url}`}
      style={{
        display: 'flex',
        alignItems: 'center'
      }}
    >
      {!textOnly && <BreadcrumbIcon item={item} />}
      <Tooltip title={url}>
        <span
          style={{
            maxWidth: route.textWidth || '200px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap'
          }}
        >
          {resolveTitle(item)}
        </span>
      </Tooltip>
    </Typography>
  );
};

export default BreadcrumbLastItem;
