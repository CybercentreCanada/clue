import { Typography, TypographyProps } from '@mui/material';
import { ReactElement } from 'react';
import { useTranslation } from 'react-i18next';

type TuiLabelProps = TypographyProps & {
  direction?: 'vertical' | 'horizontal';
  i18nKey?: string;
  label?: string;
  children: ReactElement;
};

export default function TuiLabel({ direction = 'vertical', i18nKey, label, color, children, ...props }: TuiLabelProps) {
  const { t } = useTranslation();
  const _label = i18nKey ? t(i18nKey) : label;
  return (
    <div style={{ display: 'flex', flexDirection: direction === 'horizontal' ? 'row' : 'column' }}>
      <Typography {...props}>{_label}</Typography>
      {children}
    </div>
  );
}
