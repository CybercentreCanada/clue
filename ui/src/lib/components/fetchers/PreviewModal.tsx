import type { ModalProps } from '@mui/material';
import { Modal, Paper } from '@mui/material';
import type { FetcherResult } from 'lib/types/fetcher';
import type { FC } from 'react';
import { memo } from 'react';
import type { RenderFetcherResultProps } from '../../../plugins/ClueUIPlugin';
import { FetcherResultView } from './FetcherResultView';

/**
 * The Annotation Popover is for showing a permanent popover on click with interactivity. For showing data on hover, use Annotation Popper.
 */
const PreviewModal: FC<
  {
    result: FetcherResult;
    fetcherId?: string;
    onClose?: () => void;
    slotProps?: ModalProps['slotProps'] & { fetcherResultView: Partial<RenderFetcherResultProps> };
  } & Omit<ModalProps, 'children' | 'slotProps'>
> = ({ result, slotProps, fetcherId, onClose, open = false, ...otherProps }) => {
  const { fetcherResultView, ...modalSlotProps } = slotProps;

  return (
    <Modal
      open={open}
      sx={[
        { display: 'flex', alignItems: 'center', justifyContent: 'center' },
        ...(Array.isArray(otherProps?.sx) ? otherProps?.sx : [otherProps?.sx])
      ]}
      onClose={onClose}
      slotProps={modalSlotProps}
      {...otherProps}
    >
      <Paper sx={{ maxHeight: '90%', maxWidth: '90%', p: 2, overflow: 'auto' }}>
        <FetcherResultView result={result} fetcherId={fetcherId} {...(fetcherResultView ?? {})} />
      </Paper>
    </Modal>
  );
};

export default memo(PreviewModal);
