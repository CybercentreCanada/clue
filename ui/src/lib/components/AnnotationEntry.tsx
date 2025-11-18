import { Icon } from '@iconify/react';
import { Chip, IconButton, Stack, Typography } from '@mui/material';
import Iconified from 'lib/components/display/icons/Iconified';
import type { Annotation, WithExtra } from 'lib/types/lookup';
import { twitterShort } from 'lib/utils/utils';
import type { FC } from 'react';
import { memo } from 'react';
import AnnotationBody from './AnnotationBody';
import ClassificationChip from './ClassificationChip';

/**
 * The Annotation Popover is for showing a permanent popover on click with interactivity. For showing data on hover, use Annotation Popper.
 */
const AnnotatonEntry: FC<{
  annotation: WithExtra<Annotation>;
}> = ({ annotation }) => {
  return (
    <Stack direction="column" spacing={1}>
      <Stack direction="row" spacing={1} alignItems="center">
        {annotation.analytic_icon && (
          <Icon
            style={{ alignSelf: 'center', filter: 'drop-shadow(0px 0px 1px rgb(0 0 0 / 0.4))' }}
            icon={annotation.analytic_icon}
          />
        )}
        <Typography variant="body1" sx={{ textTransform: 'capitalize', maxWidth: '275px' }}>
          {annotation.analytic ?? annotation.author}
        </Typography>
        {annotation.quantity > 1 && (
          <Typography variant="caption" color="text.secondary">
            {'(x'}
            {annotation.quantity})
          </Typography>
        )}
        <div style={{ flex: 1 }} />
        {annotation.version && (
          <Chip
            size="small"
            label={
              <>
                {'v'}
                {annotation.version.replace(/^v/, '')}
              </>
            }
          />
        )}
        {annotation.link && (
          <IconButton component="a" href={annotation.link} target="_blank" rel="noreferrer" size="small">
            <Iconified icon="ic:baseline-open-in-new" fontSize="small" />
          </IconButton>
        )}
        {annotation.classification && <ClassificationChip size="small" classification={annotation.classification} />}
      </Stack>
      <AnnotationBody annotation={annotation} />
      <Typography variant="caption" color="text.secondary">
        {annotation.summary}
      </Typography>
      <Stack direction="row">
        <Typography variant="caption" color="text.secondary" fontSize="10px">
          {twitterShort(annotation.timestamp)}
        </Typography>
        <div style={{ flex: 1 }} />
        {!!annotation.latency && (
          <Typography variant="caption" color="text.secondary" fontSize="10px">
            {Math.round(annotation.latency)}
            {'ms'}
          </Typography>
        )}
      </Stack>
    </Stack>
  );
};

export default memo(AnnotatonEntry);
