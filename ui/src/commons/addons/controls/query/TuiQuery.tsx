import { Add, Clear, Favorite, FavoriteBorder, Search } from '@mui/icons-material';
import { Alert, Box, Collapse, Divider, emphasize, LinearProgress, ListItemText, Paper, Stack } from '@mui/material';

import TuiIconButton from 'commons/addons/display/buttons/TuiIconButton';
import { TuiIconButtonMenu } from 'commons/addons/display/buttons/TuiIconButtonMenu';
import { TuiKeyboardParsedEvent } from 'commons/components/utils/keyboard';
import { FC, useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { buildQuery, TuiQueryChangeReason, TuiQueryItem, TuiQueryStoreService } from '.';
import TuiPhrase, { TuiPhraseProps } from '../phrase/TuiPhrase';
import { TuiQueryStore, TuiQueryStoreOptionProps } from './elements/TuiQueryStore';
import { TuiQueryView } from './elements/TuiQueryView';

export type TuiQueryProps = {
  q?: string;
  searching?: boolean;
  state: URLSearchParams;
  store: TuiQueryStoreService;
  onChange: (reason: TuiQueryChangeReason, fullQuery: string, state: URLSearchParams) => void;
  PhraseProps?: Omit<TuiPhraseProps, 'value' | 'InputProps' | 'onChange'>;
  StoreProps?: {
    disableGlobal?: boolean;
    OptionProps?: TuiQueryStoreOptionProps;
  };
};

export const TuiQuery: FC<TuiQueryProps> = ({
  q = 'q',
  searching = false,
  state,
  store,
  onChange,
  PhraseProps,
  StoreProps
}) => {
  const stateRef = useRef<URLSearchParams>();
  const { t } = useTranslation();
  const [query, setQuery] = useState<string>();
  const [showFavourites, setShowFarourites] = useState<boolean>(false);
  const showView = state?.has('qid') && state.getAll('qid').filter(v => !!v).length > 0;

  // Effect to trigger upstream 'onChange' callback if state/params changes.
  useEffect(() => {
    if (store.ready) {
      if (state.get(q) !== query) {
        setQuery(state.get(q) || '');
      }
      if (!stateRef.current || stateRef.current.toString() !== state.toString()) {
        stateRef.current = new URLSearchParams(state);
        onChange('init', buildQuery(q, state, store), state);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, state, store, onChange]);

  // Utility method to encapsulate logic that triggers provided upstream 'onChange' callback.
  const triggerChange = useCallback(
    (reason: TuiQueryChangeReason, newState: URLSearchParams) => {
      stateRef.current = newState;
      onChange(reason, buildQuery(q, newState, store), newState);
    },
    [q, store, onChange]
  );

  // [phrase input] Handler for when the input value of the Phrase component changes.
  const onPhraseChange = useCallback(
    (phrase: string) => {
      setQuery(phrase);
      state.set(q, phrase);
    },
    [q, state]
  );

  // [query-view] onchange handler.
  const onViewChange = useCallback(
    (nextState: URLSearchParams) => {
      triggerChange('views', nextState);
    },
    [triggerChange]
  );

  // [query-store] onchange handler.
  const onStoreChange = useCallback(
    (nextState: URLSearchParams) => {
      triggerChange('views', nextState);
    },
    [triggerChange]
  );

  // [query-input] Handler for ENTER key.
  const onKeyDown = useCallback(
    ({ isEnter }: TuiKeyboardParsedEvent) => {
      if (isEnter) {
        triggerChange('enter', state);
      }
    },
    [state, triggerChange]
  );

  // [query-input] Handler for search button.
  const onSearchBtnClick = useCallback(() => {
    triggerChange('enter', state);
  }, [state, triggerChange]);

  // [query-input] Hander for clear button.
  const onClearBtnClick = useCallback(() => {
    state.delete(q);
    triggerChange('clear', state);
  }, [q, state, triggerChange]);

  // [icon-button-select] Handler when adding/applying a new saved query/view.
  const onAddView = useCallback(
    (option: TuiQueryItem) => {
      if (state.has('qid')) {
        state.append('sep', 'AND');
      }
      state.append('qid', option.id);
      triggerChange('views', state);
    },
    [state, triggerChange]
  );

  // Render start adornments of query input/textfield
  const startRenderer = useCallback(() => {
    return (
      <>
        <TuiIconButton onClick={onSearchBtnClick}>
          <Search />
        </TuiIconButton>
        {PhraseProps.startAdornment && (
          <>
            {PhraseProps.startAdornment}
            <Box m={0.5} />
            <Divider orientation="vertical" flexItem />
          </>
        )}
      </>
    );
  }, [PhraseProps.startAdornment, onSearchBtnClick]);

  // Render end adornments of query input/textfield
  const endRenderer = useCallback(() => {
    return (
      <Stack direction="row" alignItems="center" spacing={1}>
        <TuiIconButton onClick={onClearBtnClick} sx={{ display: !query && 'none' }}>
          <Clear />
        </TuiIconButton>
        <Divider orientation="vertical" flexItem />
        <TuiIconButton tooltip={t('tui.query.save.alert')} onClick={() => setShowFarourites(!showFavourites)}>
          {showFavourites ? <Favorite /> : <FavoriteBorder />}
        </TuiIconButton>
        <TuiIconButtonMenu
          tooltip={t('tui.query.load')}
          items={store.items.map(i => ({
            key: i.id,
            onClick: () => onAddView(i),
            children: <ListItemText>{i.name}</ListItemText>
          }))}
        >
          <Add />
        </TuiIconButtonMenu>
        {PhraseProps.endAdornment && (
          <>
            <Divider orientation="vertical" flexItem />
            {PhraseProps.endAdornment}
          </>
        )}
      </Stack>
    );
  }, [t, query, store.items, PhraseProps.endAdornment, showFavourites, onAddView, onClearBtnClick]);

  return (
    state && (
      <Stack direction="column">
        <Paper
          elevation={0}
          sx={theme => ({
            border: '1px solid',
            borderColor: showView ? theme.palette.divider : 'transparent',
            borderBottomColor: 'transparent',
            borderBottomRightRadius: 0,
            borderBottomLeftRadius: 0,
            backgroundColor: emphasize(theme.palette.background.default, 0.025)
          })}
        >
          <Collapse in={showView}>
            <TuiQueryView q={q} state={state} store={store} onChange={onViewChange} />
          </Collapse>
        </Paper>

        <TuiPhrase
          {...PhraseProps}
          fullWidth
          autoComplete="off"
          value={query}
          onChange={onPhraseChange}
          onKeyDown={onKeyDown}
          startAdornment={startRenderer()}
          endAdornment={endRenderer()}
          InputProps={{
            sx: {
              ...(showFavourites ? { borderBottomRightRadius: 0, borderBottomLeftRadius: 0 } : {}),
              ...(showView ? { borderTopRightRadius: 0, borderTopLeftRadius: 0 } : {})
            }
          }}
        />
        {searching && (
          <LinearProgress
            sx={theme => ({
              mt: -0.5,
              borderBottomLeftRadius: theme.shape.borderRadius,
              borderBottomRightRadius: theme.shape.borderRadius
            })}
          />
        )}

        <Paper
          elevation={0}
          sx={theme => ({
            border: '1px solid',
            borderColor: showFavourites ? theme.palette.divider : 'transparent',
            borderTopColor: 'transparent',
            borderTopRightRadius: 0,
            borderTopLeftRadius: 0,
            backgroundColor: emphasize(theme.palette.background.default, 0.025)
          })}
        >
          <Collapse in={showFavourites}>
            <Box m={1}>
              <Alert severity="info">{t('tui.query.save.alert')}</Alert>
              <Box mb={1} />
              <TuiQueryStore q={q} store={store} state={state} onChange={onStoreChange} {...StoreProps} />
            </Box>
          </Collapse>
        </Paper>
      </Stack>
    )
  );
};
