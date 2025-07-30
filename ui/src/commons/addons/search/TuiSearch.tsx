import { FavoriteBorder } from '@mui/icons-material';
import { Box, Collapse, emphasize, LinearProgress, Paper, styled, Tooltip, useTheme } from '@mui/material';

import { ReactNode, useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { GLOBAL_COLUMN, TuiSearchColumn, TuiSearchFavouriteProvider, TuiSearchRequest } from '.';
import TuiIconButton from '../display/buttons/TuiIconButton';
import TuiChipSelect, { ChipSelectOption } from '../display/chips/TuiChipSelect';
import useTuiSearchParams from './hooks/useTuiSearchParams';
import TuiSearchModel from './models/TuiSearchModel';
import TuiSearchTerms from './models/TuiSearchTerms';
import TuiSearchExpression from './TuiSearchExpression';
import TuiSearchFavourites from './TuiSearchFavourites';
import TuiSearchInput from './TuiSearchInput';

const TuiSearchRoot = styled('div')(({ theme }) => ({
  position: 'relative',

  '.tui-search-border': {
    borderTop: '1px solid',
    borderRight: '1px solid',
    borderBottom: '1px solid',
    borderLeft: '1px solid',
    borderTopColor: emphasize(theme.palette.background.default, 0.05),
    borderRightColor: emphasize(theme.palette.background.default, 0.05),
    borderBottomColor: emphasize(theme.palette.background.default, 0.05),
    borderLeftColor: emphasize(theme.palette.background.default, 0.05)
  }
}));

export type TuiSearchChangeAction = 'input' | 'change' | 'clear';

type TuiSearchProps = {
  noFavourites?: boolean;
  searching?: boolean;
  withParams?: boolean;
  localStorage?: string;
  columns?: TuiSearchColumn[];
  model: TuiSearchModel;
  endAdornments?: ReactNode;
  favouritesProvider?: TuiSearchFavouriteProvider;
  onChange?: (state: TuiSearchModel, action?: TuiSearchChangeAction) => void;
};

// TODO: memoize this.
export default function TuiSearch({
  noFavourites,
  searching,
  withParams,
  localStorage,
  columns = [],
  model,
  endAdornments,
  favouritesProvider,
  onChange
}: TuiSearchProps) {
  const theme = useTheme();
  const containerEl = useRef<HTMLDivElement>();
  const options = useRef<TuiSearchColumn[]>([GLOBAL_COLUMN, ...columns]);
  const { t } = useTranslation();
  const { write } = useTuiSearchParams();
  const [showFavourites, setShowFavourites] = useState<boolean>(false);

  //
  useEffect(() => {
    if (withParams) {
      write(model.request());
    }
  }, [withParams, model, write]);

  // Push search changes upstream.
  const pushChange = useCallback(
    (newModel: TuiSearchModel, action: TuiSearchChangeAction) => {
      onChange(newModel, action);
    },
    [onChange]
  );

  // query change handler.
  const onFilterInputChange = useCallback(
    (terms: TuiSearchTerms, action: TuiSearchChangeAction) => {
      pushChange(action === 'clear' ? model.reset() : model.withFilters(terms), action);
    },
    [model, pushChange]
  );

  // search expression change handler.
  const onExpressionChange = useCallback(
    (newModel: TuiSearchModel) => {
      pushChange(newModel, 'change');
    },
    [pushChange]
  );

  // filter column change handler.
  const onFilterColumnChange = useCallback(
    (option: ChipSelectOption) => {
      model.filters().get().column = option.value;
      const column = options.current.find(c => c.column === option.value);
      if (column.operators && !column.operators.includes(model.filters().matcher())) {
        model.filters().withMatcher('like');
      }
      pushChange(model.rebuild(), 'change');
    },
    [model, pushChange]
  );

  // matcher change handler.
  const onMatcherChange = useCallback(
    (option: ChipSelectOption) => {
      model.filters().withMatcher(option.value);
      pushChange(model.rebuild(), 'change');
    },
    [model, pushChange]
  );

  // toggle search favourites handler.
  const onToggleShowFavourites = useCallback(() => {
    setShowFavourites(!showFavourites);
  }, [showFavourites]);

  // load search favourite handler.
  const onLoadFavourites = useCallback(
    (favourite: TuiSearchRequest) => {
      pushChange(TuiSearchModel.build(favourite), 'change');
    },
    [pushChange]
  );

  //
  const renderStart = useCallback(() => {
    const filterOptions = options.current.map(c => ({ label: c.label, i18nKey: c.i18nKey, value: c.column }));
    const filterColumn = options.current.find(c => c.column === model?.filters().get().column);
    const matcherOptions = filterColumn?.operators?.map(c => ({ label: c.toUpperCase(), value: c })) || [
      { label: 'LIKE', value: 'like' }
    ];
    return (
      <div>
        <Tooltip title={t('tui.search.tooltip.columns')}>
          <span>
            <TuiChipSelect
              color="primary"
              variant="outlined"
              sx={{ border: 'none' }}
              value={filterColumn.column}
              options={filterOptions}
              onChange={onFilterColumnChange}
            />
          </span>
        </Tooltip>

        <Tooltip title={t('tui.search.tooltip.operator')}>
          <span>
            <TuiChipSelect
              color="primary"
              variant="outlined"
              sx={{ border: 'none' }}
              disabled={matcherOptions.length <= 1}
              value={model?.filters().matcher()}
              options={matcherOptions}
              onChange={onMatcherChange}
            />
          </span>
        </Tooltip>
      </div>
    );
  }, [model, onMatcherChange, onFilterColumnChange, t]);

  //
  const renderEnd = useCallback(() => {
    return (
      <>
        {endAdornments}
        {!noFavourites && (
          <TuiIconButton
            tooltip={t('tui.search.favourtie.tooltip.toggle')}
            transparent={!showFavourites}
            color={theme.palette.primary.main}
            onClick={onToggleShowFavourites}
          >
            <FavoriteBorder />
          </TuiIconButton>
        )}
      </>
    );
  }, [theme, noFavourites, showFavourites, endAdornments, onToggleShowFavourites, t]);

  //
  return (
    !!model && (
      <TuiSearchRoot ref={containerEl} style={{ position: 'relative' }}>
        {options.current.length > 0 && (
          <TuiSearchInput
            zenMode={false}
            options={options.current}
            terms={model?.filters()}
            startAdornments={model && renderStart()}
            endAdornments={renderEnd()}
            onChange={onFilterInputChange}
          />
        )}
        {searching && <LinearProgress sx={{ marginTop: -0.5 }} />}
        <Paper sx={{ backgroundColor: emphasize(theme.palette.background.default, 0.025) }} elevation={0}>
          <Box className="tui-search-border" sx={{ padding: 1 }}>
            <Box ml={1} mr={1}>
              <TuiSearchExpression columns={options.current} model={model} onChange={onExpressionChange} />
            </Box>
            {!noFavourites && (
              <Collapse in={showFavourites}>
                <Box mt={1} ml={1} mr={1}>
                  <TuiSearchFavourites
                    localStorage={localStorage}
                    provider={favouritesProvider}
                    model={model}
                    onLoad={onLoadFavourites}
                  />
                </Box>
              </Collapse>
            )}
          </Box>
        </Paper>
      </TuiSearchRoot>
    )
  );
}
