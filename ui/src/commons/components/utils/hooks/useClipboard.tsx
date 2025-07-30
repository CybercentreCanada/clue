import { OptionsObject, useSnackbar } from 'notistack';
import { useTranslation } from 'react-i18next';

export default function useClipboard() {
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const { t } = useTranslation();
  const snackBarOptions: OptionsObject = {
    preventDuplicate: true,
    autoHideDuration: 3000,
    anchorOrigin: {
      vertical: 'bottom',
      horizontal: 'center'
    },
    SnackbarProps: {
      onClick: _snack => {
        closeSnackbar();
      }
    }
  };

  const copy = async (text: string, targetId = 'root') => {
    try {
      await navigator.clipboard.writeText(text);
      enqueueSnackbar(`${text} ${t('clipboard.success')}`, { variant: 'success', ...snackBarOptions });
    } catch (error) {
      enqueueSnackbar(`${text} ${t('clipboard.failure')}`, { variant: 'error', ...snackBarOptions });
    }
  };

  return { copy };
}
