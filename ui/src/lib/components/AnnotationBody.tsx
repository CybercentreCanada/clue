import { Icon } from '@iconify/react';
import { Box, Chip, Stack, Typography } from '@mui/material';
import type { Annotation, WithExtra } from 'lib/types/lookup';
import type { FC } from 'react';
import { memo, useMemo } from 'react';

/**
 * The Annotation Popover is for showing a permanent popover on click with interactivity. For showing data on hover, use Annotation Popper.
 */
const AnnotationBody: FC<{
  annotation: WithExtra<Annotation>;
}> = ({ annotation }) => {
  const icon = useMemo(() => {
    if (annotation.type === 'assessment') {
      return ['trivial', 'recon', 'attempt', 'compromise', 'mitigated'].includes(annotation.value as string)
        ? 'healthicons:hazardous'
        : 'fluent-mdl2:ribbon-solid';
    }

    if (annotation.type === 'opinion') {
      return annotation.value === 'benign'
        ? 'mdi:shield-check'
        : annotation.value === 'suspicious'
          ? 'mdi:warning-outline'
          : annotation.value === 'obscure'
            ? 'bi:eye-slash-fill'
            : 'mdi:warning-decagram';
    }

    return null;
  }, [annotation.type, annotation.value]);

  if (annotation.type === 'assessment') {
    return (
      <Box>
        <Chip
          size="small"
          icon={<Icon icon={icon} />}
          color={
            ['trivial', 'recon', 'attempt', 'compromise', 'mitigated'].includes(annotation.value as string)
              ? 'error'
              : 'success'
          }
          label={`${annotation.type}: ${annotation.value}`}
          sx={{ textTransform: 'capitalize' }}
        />
      </Box>
    );
  }

  if (annotation.type === 'opinion') {
    return (
      <Box>
        <Chip
          size="small"
          icon={<Icon icon={icon} />}
          color={
            {
              benign: 'success' as const,
              suspicious: 'warning' as const,
              obscure: 'error' as const,
              malicious: 'error' as const
            }[annotation.value]
          }
          label={`${annotation.type}: ${annotation.value}`}
          sx={{ textTransform: 'capitalize' }}
        />
      </Box>
    );
  }

  return (
    <Stack direction="row" alignItems="center" spacing={0.5}>
      {annotation.icon && (
        <Icon icon={annotation.icon} style={{ filter: 'drop-shadow(0px 0px 1px rgb(0 0 0 / 0.4))' }} />
      )}
      {annotation.type !== 'context' && (
        <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
          {annotation.type}:
        </Typography>
      )}
      <Typography variant="body2">{annotation.value}</Typography>
    </Stack>
  );
};

export default memo(AnnotationBody);
