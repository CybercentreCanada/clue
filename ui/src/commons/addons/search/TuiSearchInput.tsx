import { Clear } from '@mui/icons-material';
import { InputAdornment, TextField } from '@mui/material';
import { isEnter, parseEvent } from 'commons/components/utils/keyboard';
import { ChangeEvent, KeyboardEvent, ReactNode, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { TuiSearchColumn } from '.';
import TuiIconButton from '../display/buttons/TuiIconButton';
import TuiSearchTerms from './models/TuiSearchTerms';
import { TuiSearchChangeAction } from './TuiSearch';

type TuiQueryFilterProps = {
  zenMode: boolean;
  options: TuiSearchColumn[];
  terms: TuiSearchTerms;
  startAdornments?: ReactNode;
  endAdornments?: ReactNode;
  onKeyDown?: (details: { key: any; isCtrl: boolean; isEnter: boolean; isSpace: boolean; isEscape }) => void;
  onFocus?: () => void;
  onChange: (query: TuiSearchTerms, action: TuiSearchChangeAction) => void;
};

export default function TuiSearchInput({
  zenMode,
  options,
  terms,
  startAdornments,
  endAdornments,
  onKeyDown,
  onFocus,
  onChange
}: TuiQueryFilterProps) {
  const { t } = useTranslation();

  //
  const _onKeyDown = useCallback(
    (event: KeyboardEvent<HTMLElement>) => {
      if (isEnter(event.key)) {
        const term = terms.get();
        const placeholder = options.find(o => o.column === term.column);
        onChange(terms.withPlaceholder(placeholder.column).rebuild(), 'change');
      }
      if (onKeyDown) {
        onKeyDown(parseEvent(event));
      }
    },
    [terms, options, onChange, onKeyDown]
  );

  //
  const onValueChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      terms.write(event.target.value);
      onChange(terms.rebuild(), 'input');
    },
    [terms, onChange]
  );

  //
  const onClear = useCallback(() => {
    onChange(terms.reset().rebuild(), 'clear');
  }, [terms, onChange]);

  //
  const renderStart = useCallback(() => {
    return !zenMode ? (
      <InputAdornment position="start" style={{ height: 'auto' }}>
        {startAdornments}
      </InputAdornment>
    ) : null;
  }, [zenMode, startAdornments]);

  //
  const renderEnd = useCallback(() => {
    return (
      <InputAdornment position="end" style={{ height: 'auto' }}>
        {endAdornments}
        <TuiIconButton onClick={onClear} color="primary" tooltip={t('tui.search.tooltip.clear')}>
          <Clear />
        </TuiIconButton>
      </InputAdornment>
    );
  }, [endAdornments, onClear, t]);

  //
  return (
    <TextField
      fullWidth
      autoComplete="off"
      value={terms?.get().value}
      disabled={!terms}
      onChange={onValueChange}
      onKeyDown={_onKeyDown}
      onFocus={onFocus}
      InputProps={{
        startAdornment: <InputAdornment position="start">{renderStart()}</InputAdornment>,
        endAdornment: <InputAdornment position="end">{renderEnd()}</InputAdornment>
      }}
    />
  );
}
