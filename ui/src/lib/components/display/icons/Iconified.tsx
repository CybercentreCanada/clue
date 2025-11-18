import { Icon } from '@iconify/react';
import { useTheme } from '@mui/material';
import type { CSSProperties, FC } from 'react';
import { memo, useMemo } from 'react';

const Iconified: FC<{
  icon: string;
  fontSize?: 'small' | 'medium' | 'large' | 'inherit' | number;
  color?: 'disabled' | 'action' | 'inherit' | 'primary' | 'secondary' | 'success' | 'error' | 'info' | 'warning';
  style?: CSSProperties;
}> = ({ icon, fontSize = 'medium', color, style = {} }) => {
  const theme = useTheme();

  const _fontSize = useMemo(() => {
    if (fontSize === 'small') {
      return 20;
    } else if (fontSize === 'medium') {
      return 24;
    } else if (fontSize === 'large') {
      return 35;
    }

    return fontSize;
  }, [fontSize]);

  const styles = useMemo(() => {
    const _styles: CSSProperties = style;

    if (color) {
      _styles.color = theme.palette[color].main;
    }

    return _styles;
  }, [color, style, theme.palette]);

  return (
    <span style={{ display: 'flex', alignItems: 'center' }}>
      <Icon icon={icon} fontSize={_fontSize} style={styles} />
    </span>
  );
};

export default memo(Iconified);
