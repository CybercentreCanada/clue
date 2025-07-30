import { Button, Stack, Typography } from '@mui/material';
import useMyModal from 'components/hooks/useMyModal';
import type { FC } from 'react';
import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';

const ConfirmDeleteModal: FC<{ onConfirm: () => void }> = ({ onConfirm }) => {
  const { t } = useTranslation();
  const { close } = useMyModal();

  const handleConfirm = useCallback(() => {
    onConfirm();
    close();
  }, [close, onConfirm]);

  return (
    <Stack spacing={2} p={2} alignItems="start" sx={{ minWidth: '500px' }}>
      <Typography variant="h4">{t('modal.confirm.delete.title')}</Typography>
      <Typography>{t('modal.confirm.delete.description')}</Typography>
      <Stack direction="row" spacing={1} alignSelf="end">
        <Button variant="outlined" onClick={close}>
          {t('cancel')}
        </Button>
        <Button variant="outlined" onClick={handleConfirm}>
          {t('confirm')}
        </Button>
      </Stack>
    </Stack>
  );
};

export default ConfirmDeleteModal;
