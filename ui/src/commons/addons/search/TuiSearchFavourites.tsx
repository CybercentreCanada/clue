import { Delete } from '@mui/icons-material';
import { Alert, Autocomplete, Box, Button, TextField } from '@mui/material';
import { useSnackbar } from 'notistack';
import { SyntheticEvent, useState } from 'react';
import { Trans, useTranslation } from 'react-i18next';
import { useLocation } from 'react-router';
import { Link } from 'react-router-dom';
import { TuiSearchFavourite, TuiSearchFavouriteOption, TuiSearchFavouriteProvider } from '.';
import TuiIconButton from '../display/buttons/TuiIconButton';
import useTuiSearchFavourites from './hooks/useTuiSearchFavourites';
import useTuiSearchParams from './hooks/useTuiSearchParams';
import TuiSearchModel from './models/TuiSearchModel';

const DEFAULT_FAV = { name: '', search: '' };

type TuiSearchFavouritesProps = {
  model: TuiSearchModel;
  options?: TuiSearchFavourite[];
  localStorage?: string;
  provider?: TuiSearchFavouriteProvider;
  onLoad?: (request: TuiSearchFavourite) => void;
};

export default function TuiSearchFavourites({
  model,
  localStorage,
  provider: clientProvider,
  onLoad
}: TuiSearchFavouritesProps) {
  const { t } = useTranslation();
  const { uri, deserialize } = useTuiSearchParams();
  const { enqueueSnackbar } = useSnackbar();
  const { pathname } = useLocation();
  const [inputValue, setInputValue] = useState<string>('');
  const [selectedValue, setSelectedValue] = useState<TuiSearchFavouriteOption>(DEFAULT_FAV);
  const localProvider = useTuiSearchFavourites(localStorage);
  const provider = clientProvider || localProvider;
  const saveEnabled = inputValue && !provider.options.some(o => o.name === inputValue);

  const onSelect = (event: SyntheticEvent, value: TuiSearchFavouriteOption) => {
    if (typeof value === 'string' && saveEnabled) {
      onSaveClick(null, value);
    } else if (value) {
      setInputValue(value.name);
      setSelectedValue(value);
      onLoad({
        name: value.name,
        ...deserialize(value.search).request()
      });
    }
  };

  const onInputChange = event => {
    if (event) {
      setInputValue(event.currentTarget.value || '');
    }
  };

  const onSaveClick = async (event, value?: string) => {
    const success = await provider.onSave(value || inputValue, model.rebuild());
    enqueueSnackbar(
      <div>
        <Trans
          i18nKey={`tui.search.favourite.save.${success ? 'success' : 'failed'}`}
          values={{ name: value || inputValue }}
        />
      </div>,
      {
        variant: success ? 'success' : 'error',
        anchorOrigin: {
          vertical: 'bottom',
          horizontal: 'center'
        }
      }
    );
  };

  const onDeleteClick = async (event, option: TuiSearchFavouriteOption) => {
    event.stopPropagation();
    event.preventDefault();
    const success = await provider.onDelete(option);
    enqueueSnackbar(
      <div>
        <Trans
          i18nKey={`tui.search.favourite.delete.${success ? 'success' : 'failed'}`}
          values={{ name: option.name }}
        />
      </div>,
      {
        variant: success ? 'success' : 'error',
        anchorOrigin: {
          vertical: 'bottom',
          horizontal: 'center'
        }
      }
    );
  };

  return (
    <Box mt={2}>
      <Alert severity="info">{t('tui.search.favourite.alert')}</Alert>

      <Box m={2} />

      <Autocomplete
        fullWidth
        freeSolo
        autoHighlight
        multiple={false}
        inputValue={inputValue}
        value={selectedValue}
        placeholder={t('tui.search.favourite.title')}
        options={provider.options}
        getOptionDisabled={() => false}
        getOptionLabel={(option: TuiSearchFavouriteOption) => {
          return option.name ? option.name : '';
        }}
        renderInput={params => <TextField {...params} fullWidth label={t('tui.search.favourite.title')} />}
        renderOption={(props, option) => (
          <Link
            key={option.name}
            to={uri(pathname, option.search)}
            style={{ textDecoration: 'none', color: 'inherit' }}
          >
            <li {...props}>
              {option.name}
              <Box flex={1} />
              <TuiIconButton
                onClick={event => onDeleteClick(event, option)}
                tooltip={t('tui.search.favourite.tooltip.delete')}
              >
                <Delete />
              </TuiIconButton>
            </li>
          </Link>
        )}
        onInputChange={onInputChange}
        onChange={onSelect}
      />
      <Box margin={2} />
      <Button variant="contained" color="primary" disabled={!saveEnabled} onClick={onSaveClick}>
        {t('save')}
      </Button>
    </Box>
  );
}
