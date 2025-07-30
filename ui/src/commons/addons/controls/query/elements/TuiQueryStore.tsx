import { Delete, Input } from '@mui/icons-material';
import {
  Autocomplete,
  AutocompleteChangeReason,
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
  Typography
} from '@mui/material';
import TuiIconButton from 'commons/addons/display/buttons/TuiIconButton';
import useLocalStorageItem from 'commons/components/utils/hooks/useLocalStorageItem';
import { ChangeEvent, FC, ReactNode, SyntheticEvent, useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { buildQuery, LS_KEY_QUERY_APPEND, LS_KEY_QUERY_GLOBAL, TuiQueryItem, TuiQueryStoreService } from '..';

export type TuiQueryStoreOptionProps = {
  renderer?: (query: TuiQueryItem) => ReactNode;
  menuRenderer?: (query: TuiQueryItem) => ReactNode;
};

export type TuiQueryStoreProps<T extends TuiQueryItem = TuiQueryItem> = {
  disableGlobal?: boolean;
  q: string;
  state: URLSearchParams;
  store: TuiQueryStoreService<T>;
  onChange: (nextState: URLSearchParams) => void;
  OptionProps?: TuiQueryStoreOptionProps;
};

export const TuiQueryStore: FC<TuiQueryStoreProps> = ({ disableGlobal, q, state, store, onChange, OptionProps }) => {
  const { t } = useTranslation();
  const [name, setName] = useState<string>('');
  const [includeSelections, setIncludeSelections] = useLocalStorageItem<boolean>(LS_KEY_QUERY_APPEND, true);
  const [global, setGlobal] = useLocalStorageItem(LS_KEY_QUERY_GLOBAL, false);
  const saveDisabled =
    !name ||
    store.items.some(v => v.name === name) ||
    (!includeSelections && !state.get(q)) ||
    (includeSelections && !state.has('qid') && !state.get(q));

  const onInputChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    if (event) {
      setName(event.currentTarget.value || '');
    }
  }, []);

  const onSaveClick = useCallback(async () => {
    const fullQuery = includeSelections ? buildQuery(q, state, store) : state.get(q);
    const result = await store.onCreate(name, fullQuery, global);

    setName('');
    state.delete(q);
    if (includeSelections) {
      state.delete('qid');
      state.delete('sep');
    } else if (state.has('qid')) {
      state.append('sep', 'AND');
    }

    state.append('qid', result);

    onChange(new URLSearchParams(state.toString()));
  }, [global, name, includeSelections, q, state, store]);

  const onDeleteClick = useCallback(
    async (item: TuiQueryItem) => {
      const success = await store.onDelete(item.id);
      if (success) {
      }
    },
    [store]
  );

  const onLoadClick = useCallback(
    (item: TuiQueryItem) => {
      state.set(q, item.value);
      onChange(new URLSearchParams(state.toString()));
    },
    [q, state, onChange]
  );

  const onSelectionChange = useCallback(
    (event: SyntheticEvent, values: TuiQueryItem[], reason: AutocompleteChangeReason) => {
      const item = values[0];
      if (state.has('qid')) {
        state.append('sep', 'AND');
      }
      state.append('qid', item.id);

      onChange(new URLSearchParams(state.toString()));
    },
    [state, onChange]
  );

  const onGlobalToggle = useCallback(
    (event: SyntheticEvent, checked: boolean) => {
      setGlobal(checked);
    },
    [setGlobal]
  );

  return (
    <Box>
      <Autocomplete
        freeSolo
        fullWidth
        autoHighlight
        disableCloseOnSelect
        multiple // This allows consecutive option click to toggle.
        value={[]} // Trick multiple to only have one selected value.
        inputValue={name}
        options={store.items}
        renderInput={params => <TextField {...params} fullWidth />}
        renderOption={(props, option) => (
          <li {...props} key={option.id}>
            <Stack direction="row" alignItems="center" style={{ width: '100%' }}>
              <Stack direction="column" style={{ width: '100%' }} flex={1}>
                {OptionProps.renderer ? (
                  OptionProps.renderer(option)
                ) : (
                  <>
                    <Stack direction="row" alignItems="center">
                      <Typography>{option.name}</Typography>
                    </Stack>
                    <Stack direction="row" alignItems="center">
                      <Box mr={1.5} />
                      <Typography variant="caption" color="primary">
                        {option.value}
                      </Typography>
                    </Stack>
                  </>
                )}
              </Stack>
              <Stack
                direction="row"
                alignItems="center"
                flex={0}
                onClick={event => {
                  event.stopPropagation();
                }}
              >
                {OptionProps?.menuRenderer && OptionProps.menuRenderer(option)}
                <TuiIconButton tooltip={t('tui.query.store.load')} onClick={() => onLoadClick(option)}>
                  <Input />
                </TuiIconButton>
                <TuiIconButton
                  tooltip={t('tui.query.store.delete')}
                  onClick={() => onDeleteClick(option)}
                  disabled={state.getAll('qid').some(qid => qid === option.id)}
                >
                  <Delete />
                </TuiIconButton>
              </Stack>
            </Stack>
          </li>
        )}
        getOptionDisabled={() => false}
        getOptionLabel={(option: TuiQueryItem) => {
          return option.name ? option.name : '';
        }}
        onInputChange={onInputChange}
        onChange={onSelectionChange}
      />
      <Box m={1} />
      <Stack direction="row" alignItems="center">
        <Button variant="contained" size="small" onClick={onSaveClick} disabled={saveDisabled}>
          {t('save')}
        </Button>
        <Box m={1} />
        {!disableGlobal && (
          <FormControlLabel
            control={<Switch size="small" disabled={saveDisabled} value={global} onChange={onGlobalToggle} />}
            label={
              <Typography
                variant="caption"
                sx={theme => ({ color: saveDisabled ? theme.palette.text.disabled : theme.palette.primary.main })}
              >
                {t('global')}
              </Typography>
            }
          />
        )}
        <FormControlLabel
          control={<Checkbox checked={includeSelections} onClick={() => setIncludeSelections(!includeSelections)} />}
          label={
            <Typography
              variant="caption"
              sx={theme => ({ color: saveDisabled ? theme.palette.text.disabled : theme.palette.primary.main })}
            >
              {t('tui.query.save.append')}
            </Typography>
          }
        />
      </Stack>
    </Box>
  );
};
