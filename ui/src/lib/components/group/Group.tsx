import type { StackProps } from '@mui/material';
import { Stack } from '@mui/material';
import type { ClueGroupContextProps } from 'lib/hooks/ClueGroupContext';
import { ClueGroupProvider } from 'lib/hooks/ClueGroupContext';
import type { FC, PropsWithChildren } from 'react';
import { memo } from 'react';
import GroupControl from './GroupControl';

interface ClueGroupProps extends ClueGroupContextProps {
  showHeader?: boolean;
  slotProps?: {
    stack?: StackProps;
  };
}

/**
 * The Annotation Popover is for showing a permanent popover on click with interactivity. For showing data on hover, use Annotation Popper.
 */
const Group: FC<PropsWithChildren<ClueGroupProps>> = ({ children, showHeader = true, slotProps, ...groupProps }) => {
  return (
    <ClueGroupProvider {...groupProps}>
      {showHeader ? (
        <Stack direction="column" alignSelf="stretch" {...(slotProps?.stack ?? {})}>
          <GroupControl />
          {children}
        </Stack>
      ) : (
        children
      )}
    </ClueGroupProvider>
  );
};

export default memo(Group);
