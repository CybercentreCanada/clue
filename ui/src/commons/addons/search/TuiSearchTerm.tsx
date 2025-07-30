import { Cancel } from '@mui/icons-material';
import { Chip, Tooltip } from '@mui/material';
import { memo, ReactElement, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import TuiChipSelect, { ChipSelectOption } from '../display/chips/TuiChipSelect';
import { isSeparator, isSorter, SEPARATORS, TuiSearchSeparator, TuiSearchTerm } from './models/TuiSearchTerms';

type TuiQueryTermProps = TuiSearchTerm<any> & {
  cursor: boolean;
  icon?: ReactElement;
  onSeparatorChange?: (id: string, value: TuiSearchSeparator) => void;
  onClick: (id: string) => void;
  onDelete: (id: string) => void;
};

const TuiQueryTerm = ({
  id,
  column,
  operator,
  value,
  cursor,
  icon,
  onSeparatorChange,
  onClick,
  onDelete
}: TuiQueryTermProps) => {
  const separator = isSeparator(operator);
  const { t } = useTranslation();

  const _onClick = useCallback(() => {
    onClick(id);
  }, [id, onClick]);

  const _onDelete = useCallback(() => {
    onDelete(id);
  }, [id, onDelete]);

  const _onSeparatorChange = useCallback(
    (selection: ChipSelectOption) => {
      if (onSeparatorChange) {
        onSeparatorChange(id, selection.value);
      }
    },
    [id, onSeparatorChange]
  );

  const label = useMemo(() => {
    const sorter = isSorter(operator);
    return separator ? (
      <span>{operator}</span>
    ) : sorter ? (
      <span>{`${column} ${value}`}</span>
    ) : (
      <span>{`${column} ${operator} ${value}`}</span>
    );
  }, [separator, operator, column, value]);

  if (separator) {
    return (
      <Tooltip title={t('tui.search.expression.tooltip.changeseparator')}>
        <TuiChipSelect
          size="small"
          variant="outlined"
          sx={{ margin: 0.5 }}
          label={label}
          value={operator}
          options={SEPARATORS.map(s => ({ label: s, value: s }))}
          onChange={_onSeparatorChange}
        />
      </Tooltip>
    );
  }

  return (
    <Chip
      size="small"
      icon={icon}
      color={cursor ? 'primary' : 'default'}
      variant={separator ? 'outlined' : 'filled'}
      label={label}
      onClick={!separator ? _onClick : null}
      onDelete={!separator ? _onDelete : null}
      deleteIcon={<Cancel />}
      sx={{ margin: 0.5 }}
    />
  );
};

export default memo(TuiQueryTerm);
