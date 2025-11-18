import type { PopoverActions, PopoverProps } from '@mui/material';
import { Popover } from '@mui/material';
import type { Selector } from 'lib/types/lookup';
import type { FC } from 'react';
import React, { useEffect, useRef, useState } from 'react';
import AnnotationDetails from './AnnotationDetails';

/**
 * The Annotation Popover is for showing a permanent popover on click with interactivity. For showing data on hover, use Annotation Popper.
 */
const AnnotationDetailPopover: FC<
  {
    anchorEl: HTMLElement;
    enrichRequest: Selector;
    onClose: PopoverProps['onClose'];
    open: boolean;
  } & Omit<PopoverProps, 'open'>
> = React.memo(({ anchorEl, enrichRequest, open, onClose, ...otherProps }) => {
  const actionRef = useRef<PopoverActions>();

  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!open) {
      setReady(false);
    }
  }, [open]);

  return (
    <Popover
      anchorOrigin={{ horizontal: 'left', vertical: 'bottom' }}
      {...otherProps}
      action={actionRef}
      open={!!(open && ready)}
      keepMounted={open}
      anchorEl={anchorEl}
      onClose={onClose}
      slotProps={{
        ...(otherProps.slotProps ?? {}),
        paper: {
          ...(otherProps.slotProps?.paper ?? {}),
          sx: [
            {
              maxHeight: 'min(600px, 95vh)',
              overflowY: 'auto',
              maxWidth: '500px',
              width: '100%',
              zIndex: anchorEl?.computedStyleMap?.().get('z-index')?.toString() || 2
            }
          ]
        }
      }}
      onClick={e => {
        e.preventDefault();
        e.stopPropagation();

        otherProps.onClick?.(e);
      }}
    >
      <AnnotationDetails
        enrichRequest={enrichRequest}
        setReady={setReady}
        updatePosition={() => actionRef.current?.updatePosition()}
      />
    </Popover>
  );
});

export default AnnotationDetailPopover;
