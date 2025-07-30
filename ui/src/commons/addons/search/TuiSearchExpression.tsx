import { Add } from '@mui/icons-material';
import { Tooltip, Typography } from '@mui/material';
import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { nextSortState, sortIcon, TuiSearchColumn } from '.';
import TuiChipSelect, { ChipSelectOption } from '../display/chips/TuiChipSelect';
import TuiSearchModel from './models/TuiSearchModel';
import { SEPARATORS, TuiSearchSeparator } from './models/TuiSearchTerms';
import TuiQueryTerm from './TuiSearchTerm';

type TuiSearchExpressionProps = {
  columns: TuiSearchColumn[];
  model: TuiSearchModel;
  onChange?: (model: TuiSearchModel) => void;
};

export default function TuiSearchExpression({ columns, model, onChange }: TuiSearchExpressionProps) {
  const sorters = columns.filter(c => c.column !== '*').filter(c => !model.sorters().hasColumn(c.column));
  const { t } = useTranslation();
  const [, setFilterSelectValue] = useState<TuiSearchColumn>(columns[0]);
  const [separatorSelectValue, setSeparatorSelectValue] = useState<string>(model.filters().separator());

  const onChangeSeparator = useCallback(
    (option: ChipSelectOption) => {
      setSeparatorSelectValue(option.value);
      if (onChange) {
        model.filters().withSeparator(option.value);
        onChange(model.rebuild());
      }
    },
    [model, onChange]
  );

  const onAddMatcher = useCallback(
    (option: ChipSelectOption) => {
      setFilterSelectValue(option.value);
      if (onChange) {
        model.filters().withPlaceholder(option.value.column);
        onChange(model.rebuild());
      }
    },
    [model, onChange]
  );

  const onAddSorter = useCallback(
    (option: ChipSelectOption) => {
      if (onChange) {
        model.sorters().orderBy(option.value.column, 'asc');
        onChange(model.rebuild());
      }
    },
    [model, onChange]
  );

  const onMatcherClick = useCallback(
    (id: string) => {
      const term = model.filters().findById(id);
      model.filters().move(term);
      onChange(model.rebuild());
    },
    [model, onChange]
  );

  const onMatcherDelete = useCallback(
    (id: string) => {
      const term = model.filters().findById(id);
      model.filters().remove(term);
      onChange(model.rebuild());
    },
    [model, onChange]
  );

  const onSorterClick = useCallback(
    (id: string) => {
      const term = model.sorters().findById(id);
      term.value = nextSortState(term.value, 'asc');
      model.sorters().move(term);
      onChange(model.rebuild());
    },
    [model, onChange]
  );

  const onSorterDelete = useCallback(
    (id: string) => {
      const term = model.sorters().findById(id);
      model.sorters().remove(term);
      onChange(model.rebuild());
    },
    [model, onChange]
  );

  const onSeparatorChange = useCallback(
    (id: string, separator: TuiSearchSeparator) => {
      model.filters().findById(id).operator = separator;
      onChange(model.rebuild());
    },
    [model, onChange]
  );

  return (
    <div>
      <Typography component="span" variant="caption" sx={{ fontStyle: 'italic', fontWeight: 'bold', marginRight: 1 }}>
        {t('tui.search.expression.searching')}
      </Typography>
      {model
        .filters()
        .terms()
        .map(term => (
          <TuiQueryTerm
            key={term.id}
            {...term}
            cursor={term === model.filters().get()}
            onSeparatorChange={onSeparatorChange}
            onClick={onMatcherClick}
            onDelete={onMatcherDelete}
          />
        ))}
      {model.filters().count() > 0 && (
        <Tooltip title={t('tui.search.expression.tooltip.nextseparator')}>
          <span>
            <TuiChipSelect
              size="small"
              color="primary"
              variant="outlined"
              sx={{ margin: 0.5 }}
              value={separatorSelectValue}
              options={SEPARATORS.map(s => ({ label: s, value: s }))}
              onChange={onChangeSeparator}
            />
          </span>
        </Tooltip>
      )}

      <Tooltip title={t('tui.search.expression.tooltip.newfilter')}>
        <span>
          <TuiChipSelect
            size="small"
            color="primary"
            variant="outlined"
            sx={{ margin: 0.5 }}
            icon={<Add fontSize="small" />}
            value={columns.find(c => c.column === model.filters().get().column)}
            options={columns.map(c => ({ label: c.label, i18nKey: c.i18nKey, value: c }))}
            onChange={onAddMatcher}
          />
        </span>
      </Tooltip>

      <Typography
        component="span"
        variant="caption"
        sx={{ fontStyle: 'italic', fontWeight: 'bold', marginLeft: 1, marginRight: 1 }}
      >
        {t('tui.search.expression.sortedby')}
      </Typography>
      {model
        .sorters()
        .terms()
        .map(term => (
          <TuiQueryTerm
            key={term.id}
            {...term}
            cursor={term === model.sorters().get()}
            icon={sortIcon(term.value)}
            onClick={onSorterClick}
            onDelete={onSorterDelete}
          />
        ))}
      {sorters.length > 0 && (
        <Tooltip title={t('tui.search.expression.tooltip.newsorter')}>
          <span>
            <TuiChipSelect
              size="small"
              color="primary"
              variant="outlined"
              sx={{ margin: 0.5 }}
              icon={<Add fontSize="small" />}
              value={sorters[0]}
              options={sorters.map(c => ({ label: c.label, i18nKey: c.i18nKey, value: c }))}
              onChange={onAddSorter}
            />
          </span>
        </Tooltip>
      )}
    </div>
  );
}
