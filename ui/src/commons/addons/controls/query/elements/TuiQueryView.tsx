import { Clear, Delete, Input } from '@mui/icons-material';
import { Box, Chip, Stack, Tooltip } from '@mui/material';
import TuiIconButton from 'commons/addons/display/buttons/TuiIconButton';
import TuiChipSelect, { ChipSelectOption } from 'commons/addons/display/chips/TuiChipSelect';
import { FC, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { v4 as uuid } from 'uuid';
import { buildQuery, TuiQueryStoreService } from '..';

type TuiQueryViewProps = {
  q: string;
  state: URLSearchParams;
  store: TuiQueryStoreService;
  onChange: (nextState: URLSearchParams) => void;
};

export const TuiQueryView: FC<TuiQueryViewProps> = ({ q, state, store, onChange }) => {
  const { t } = useTranslation();

  const items = useMemo(
    () =>
      Array.from(state.entries())
        .filter(([key, value]) => key !== q && !!value)
        .map(([key, value]) => {
          return { key: uuid(), item: { key, value } };
        }),
    [q, state]
  );

  const onItemChange = useCallback(
    (parentKey: string, value: string) => {
      state.delete('qid');
      state.delete('sep');
      items.forEach(item => {
        if (item.key === parentKey) {
          state.append(item.item.key, value);
        } else {
          state.append(item.item.key, item.item.value);
        }
      });
      onChange(new URLSearchParams(state.toString()));
    },
    [state, items, onChange]
  );

  const onItemDelete = useCallback(
    (parentKey: string) => {
      state.delete('qid');
      state.delete('sep');
      items.forEach((item, index, _items) => {
        // Remove the corresponding qid
        if (item.key === parentKey) {
          return;
        }

        // Remove the corresponding sep
        if (_items[index + 1]?.key === parentKey) {
          return;
        }

        // If the first qid was the one removed, also remove the first sep
        if (index === 1 && state.getAll('qid').length < 1) {
          return;
        }

        state.append(item.item.key, item.item.value);
      });

      onChange(new URLSearchParams(state.toString()));
    },
    [state, items, onChange]
  );

  const onClearViews = useCallback(() => {
    state.delete('qid');
    state.delete('sep');
    onChange(new URLSearchParams(state.toString()));
  }, [state, onChange]);

  const onLoadViews = useCallback(() => {
    const query = buildQuery(q, state, store);
    state.delete('qid');
    state.delete('sep');
    state.set(q, query);
    onChange(new URLSearchParams(state.toString()));
  }, [q, state, store, onChange]);

  return (
    <Stack direction="row" m={1} gap={1}>
      <Stack direction="row" alignItems="center" gap={1} flexWrap="wrap">
        {items.map((i, position) => {
          const item = store.items.find(si => si.id === i.item.value);
          return i.item.key === 'qid' ? (
            <Tooltip key={i.key} title={item?.value ?? ''}>
              <Chip
                key={i.key}
                size="small"
                color={!item ? 'error' : 'default'}
                sx={{ '& > span': { pl: 0 } }}
                label={
                  item ? (
                    <TuiChipSelect
                      size="small"
                      key={i.key}
                      value={i.item.value}
                      deleteIcon={<Delete />}
                      options={store.items.map(_item => ({ value: _item.id, label: _item.name }))}
                      onChange={(selection: ChipSelectOption<string>) => onItemChange(i.key, selection.value)}
                    />
                  ) : (
                    <Box component="span" sx={{ pl: 1 }}>
                      {t('tui.query.invalid')}
                    </Box>
                  )
                }
                onDelete={() => onItemDelete(i.key)}
              />
            </Tooltip>
          ) : i.item.key === 'sep' ? (
            <TuiChipSelect
              key={i.key}
              size="small"
              variant="outlined"
              value={i.item.value}
              onChange={(selection: ChipSelectOption<string>) => onItemChange(i.key, selection.value)}
              options={[
                { value: 'AND', label: 'AND' },
                { value: 'OR', label: 'OR' }
              ]}
            />
          ) : null;
        })}
      </Stack>
      <Box flex={1} />
      <Stack direction="row">
        <TuiIconButton tooltip={t('tui.query.views.load')} onClick={onLoadViews}>
          <Input />
        </TuiIconButton>
        <TuiIconButton tooltip={t('tui.query.views.clear')} onClick={onClearViews}>
          <Clear />
        </TuiIconButton>
      </Stack>
    </Stack>
  );
};
