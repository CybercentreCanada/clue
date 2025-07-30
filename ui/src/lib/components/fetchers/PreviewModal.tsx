import type { ModalProps } from '@mui/material';
import { Modal, Paper } from '@mui/material';
import type { FetcherResult } from 'lib/types/fetcher';
import type { FC } from 'react';
import { memo } from 'react';

/**
 * The Annotation Popover is for showing a permanent popover on click with interactivity. For showing data on hover, use Annotation Popper.
 */
const PreviewModal: FC<
  {
    result: FetcherResult;
    onClose?: () => void;
  } & Omit<ModalProps, 'children'>
> = ({ result, onClose, open = false, ...otherProps }) => {
  return (
    <Modal
      open={open}
      sx={[
        { display: 'flex', alignItems: 'center', justifyContent: 'center' },
        ...(Array.isArray(otherProps?.sx) ? otherProps?.sx : [otherProps?.sx])
      ]}
      onClose={onClose}
      {...otherProps}
    >
      <Paper sx={{ maxHeight: '90%', maxWidth: '90%', p: 2, overflow: 'auto' }}>
        {result?.format === 'image' && (
          <img src={result.data.image} alt={result.data.alt} style={{ maxWidth: '100%' }} />
        )}
      </Paper>
    </Modal>
  );
};

export default memo(PreviewModal);
