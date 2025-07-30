import { useTheme } from '@mui/material';
import type { FC } from 'react';
import type { IconProps } from './BaseIcon';
import BaseIcon from './BaseIcon';

const NetworkIcon: FC<IconProps> = props => {
  const theme = useTheme();

  return (
    <BaseIcon
      {...props}
      style={{ fill: theme.palette.getContrastText(theme.palette.info.dark), ...props.style }}
      circleStyle={{ fill: theme.palette.info.dark, ...props.style }}
    >
      <path
        style={{ transform: 'scale(0.75) translateX(16%) translateY(-18%)' }}
        d="M120-80v-280h120v-160h200v-80H320v-280h320v280H520v80h200v160h120v280H520v-280h120v-80H320v80h120v280H120Zm280-600h160v-120H400v120ZM200-160h160v-120H200v120Zm400 0h160v-120H600v120ZM480-680ZM360-280Zm240 0Z"
      />
    </BaseIcon>
  );
};

export default NetworkIcon;
