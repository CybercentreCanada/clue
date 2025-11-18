import { Icon } from '@iconify/react';
import type { PopperProps } from '@mui/material';
import { Divider, Fade, Paper, Popper, Stack, Typography, useTheme } from '@mui/material';
import { CluePopupContext } from 'lib/hooks/CluePopupContext';
import useAnnotations from 'lib/hooks/useAnnotations';
import type { Selector } from 'lib/types/lookup';
import { twitterShort } from 'lib/utils/utils';
import type { FC } from 'react';
import { useCallback, useMemo } from 'react';
import { useContextSelector } from 'use-context-selector';

/**
 * The Annotation Preview is for showing a temporary popper on hover.
 */
const AnnotationPreview: FC<
  {
    annotationType:
      | 'opinion'
      | 'frequency'
      | 'owner'
      | 'assessment'
      | 'context'
      | 'activity'
      | 'mitigation'
      | 'actionResults';
    anchorEl: HTMLElement;
    enrichRequest: Selector;
    open: boolean;
  } & Omit<PopperProps, 'open'>
> = ({ annotationType, anchorEl, enrichRequest, open, ...otherProps }) => {
  const theme = useTheme();

  const _detailsContent = useContextSelector(CluePopupContext, state => state.__detailsContent);

  const [annotations] = useAnnotations(enrichRequest?.type, enrichRequest?.value, enrichRequest?.classification);
  const filteredAnnotations = useMemo(
    () =>
      annotationType === 'actionResults' ? [] : annotations.filter(annotation => annotation.type === annotationType),
    [annotationType, annotations]
  );

  const getZIndex = useCallback((_anchorEl: Element) => {
    try {
      const zIndex = parseInt(window.getComputedStyle(_anchorEl, null).getPropertyValue('z-index'));
      if (isNaN(zIndex)) {
        return getZIndex(_anchorEl.parentElement);
      }

      return (zIndex + 2).toString();
    } catch {
      return '2';
    }
  }, []);

  if (!filteredAnnotations.length && !_detailsContent) {
    return null;
  }

  return (
    <Popper
      {...otherProps}
      open={open}
      anchorEl={anchorEl}
      placement="bottom-start"
      sx={[{ zIndex: getZIndex(anchorEl) }, ...(Array.isArray(otherProps.sx) ? otherProps.sx : [otherProps.sx])]}
    >
      <Fade in={!!anchorEl}>
        <Paper sx={{ overflowY: 'auto', maxWidth: '500px', boxShadow: theme.shadows[2] }}>
          <Stack direction="column" sx={{ p: 1 }} spacing={1} divider={<Divider orientation="horizontal" />}>
            {_detailsContent ??
              filteredAnnotations.map(annotation => (
                <Stack
                  key={
                    annotation.analytic +
                    annotation.author +
                    annotation.value +
                    annotation.link +
                    annotation.summary +
                    annotation.timestamp
                  }
                  direction="column"
                  spacing={1}
                >
                  <Stack direction="row" spacing={1} alignItems="center">
                    {annotation.analytic_icon && (
                      <Icon
                        icon={annotation.analytic_icon}
                        style={{ filter: 'drop-shadow(0px 0px 1px rgb(0 0 0 / 0.4))' }}
                      />
                    )}
                    <Typography variant="body1" sx={{ textTransform: 'capitalize' }}>
                      {annotation.analytic ?? annotation.author}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      ({twitterShort(annotation.timestamp)})
                    </Typography>
                  </Stack>
                  <Typography variant="body2">{annotation.summary}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {annotation.value}
                  </Typography>
                </Stack>
              ))}
          </Stack>
        </Paper>
      </Fade>
    </Popper>
  );
};

export default AnnotationPreview;
