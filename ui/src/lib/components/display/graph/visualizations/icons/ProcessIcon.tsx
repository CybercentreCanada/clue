import { colors, useTheme } from '@mui/material';
import type { FC } from 'react';
import type { IconProps } from './BaseIcon';
import BaseIcon from './BaseIcon';

const ProcessIcon: FC<IconProps> = props => {
  const theme = useTheme();

  return (
    <BaseIcon
      {...props}
      style={{ fill: theme.palette.getContrastText(colors.grey[500]), ...props.style }}
      circleStyle={{ fill: colors.grey[500], ...props.style }}
    >
      <path d="M360-360v-240h240v240H360Zm80-80h80v-80h-80v80Zm-80 320v-80h-80q-33 0-56.5-23.5T200-280v-80h-80v-80h80v-80h-80v-80h80v-80q0-33 23.5-56.5T280-760h80v-80h80v80h80v-80h80v80h80q33 0 56.5 23.5T760-680v80h80v80h-80v80h80v80h-80v80q0 33-23.5 56.5T680-200h-80v80h-80v-80h-80v80h-80Zm320-160v-400H280v400h400ZM480-480Z" />
    </BaseIcon>
  );
};

export default ProcessIcon;
