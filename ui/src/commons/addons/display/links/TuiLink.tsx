import { Link as MuiLink, LinkProps as MuiLinkProps } from '@mui/material';
import { FC, memo } from 'react';
import { Link, LinkProps } from 'react-router-dom';

export type TuiLinkProps = { route?: string; noDecoration?: boolean } & MuiLinkProps & Omit<LinkProps, 'to'>;

export const TuiLink: FC<TuiLinkProps> = memo(({ href, route, noDecoration, children, ...linkProps }) => {
  if (href) {
    return (
      <MuiLink
        {...linkProps}
        href={href}
        style={{
          ...linkProps.style,
          textDecoration: noDecoration && 'none',
          color: noDecoration && 'inherit'
        }}
      >
        {children}
      </MuiLink>
    );
  } else if (route) {
    return (
      <Link
        {...linkProps}
        to={route}
        style={{
          ...linkProps.style,
          textDecoration: noDecoration && 'none',
          color: noDecoration && 'inherit'
        }}
      >
        {children}
      </Link>
    );
  }
  return <>{children}</>;
});
