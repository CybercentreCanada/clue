import { Badge } from '@mui/material';
import type { PropsWithChildren } from 'react';
import { Children, cloneElement, forwardRef } from 'react';

const CountBadge = forwardRef<
  HTMLElement,
  PropsWithChildren<{
    color?: 'error' | 'secondary' | 'default' | 'primary' | 'info' | 'success' | 'warning';
    count: number;
    disabled?: boolean;
  }>
>(({ children, color = 'primary', count, disabled, ...props }, ref) => {
  if (disabled) {
    return cloneElement(Children.only(children) as any, { ref, ...props });
  }

  return (
    <Badge
      ref={ref}
      {...props}
      badgeContent={count < 100 ? count : '99+'}
      color={color}
      sx={theme => ({
        '& .MuiBadge-badge': {
          backgroundColor: 'transparent',
          color: theme.palette[color].main,
          fontWeight: 'bold',
          right: 0,
          top: 0,
          transform: `translateY(-25%) translateX(${Math.min(Math.ceil(Math.log10(count)), 3) * 10}%)`,
          px: 0,
          fontSize: '.85rem'
        },
        pr: 1.5
      })}
    >
      {children}
    </Badge>
  );
});

export default CountBadge;
