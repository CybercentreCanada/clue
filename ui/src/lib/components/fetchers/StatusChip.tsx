import { Icon } from '@iconify/react';
import type { ChipProps } from '@mui/material';
import { Chip, useTheme } from '@mui/material';
import { ClueComponentContext } from 'lib/hooks/ClueComponentContext';
import type { FetcherStatusResult } from 'lib/types/fetcher';
import type { FC } from 'react';
import { useContextSelector } from 'use-context-selector';

const StatusChip: FC<ChipProps & { data: FetcherStatusResult['data'] }> = ({ data, ...chipProps }) => {
  const theme = useTheme();

  const { i18n, t } = useContextSelector(ClueComponentContext, ctx => ctx.i18next);

  if (data?.empty) {
    return null;
  }

  return (
    <Chip
      icon={data.icon && <Icon icon={data.icon} fontSize="1.25rem" />}
      deleteIcon={
        <a href={data.link} rel="noreferrer" target="_blank" style={{ display: 'flex', alignItems: 'center' }}>
          <Icon icon="mdi:open-in-new" color={theme.palette.text.primary} fontSize="1.25rem" />
        </a>
      }
      {...chipProps}
      label={(data.labels.find(label => label.language === i18n.language) ?? data.labels[0])?.label ?? t('unknown')}
      sx={[
        ...(Array.isArray(chipProps?.sx) ? chipProps?.sx : [chipProps?.sx]),
        data.color && { backgroundColor: data.color }
      ]}
    />
  );
};

export default StatusChip;
