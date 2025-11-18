import { useTheme } from '@mui/material';
import type { FC } from 'react';
import type { IconProps } from './BaseIcon';
import BaseIcon from './BaseIcon';

const HostIcon: FC<IconProps> = props => {
  const theme = useTheme();

  return (
    <BaseIcon
      {...props}
      style={{ fill: theme.palette.getContrastText(theme.palette.info.dark), ...props.style }}
      circleStyle={{ fill: theme.palette.info.dark, ...props.style }}
    >
      <path
        style={{ transform: 'scale(0.75) translateX(16%) translateY(-18%)' }}
        d="M40-120v-80h880v80H40Zm120-120q-33 0-56.5-23.5T80-320v-440q0-33 23.5-56.5T160-840h640q33 0 56.5 23.5T880-760v440q0 33-23.5 56.5T800-240H160Zm0-80h640v-440H160v440Zm0 0v-440 440Z"
      />
    </BaseIcon>
  );
};

export default HostIcon;
