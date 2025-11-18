import { Box, MenuItem, MenuList, MenuListProps, Typography } from '@mui/material';
import { KeyboardEvent, memo, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { AppSearchItem } from '../app/AppSearchService';
import useAppSearchService from '../app/hooks/useAppSearchService';

import AppListEmpty from '../display/AppListEmpty';
import { parseEvent } from '../utils/keyboard';

type AppSearchResultProps = MenuListProps;

const AppSearchResult = ({ ...menuProps }: AppSearchResultProps) => {
  const { t } = useTranslation();
  const { state, service } = useAppSearchService();

  const onKeyDown = (event: KeyboardEvent<HTMLElement>, item: AppSearchItem) => {
    const { isEnter, isEscape } = parseEvent(event);
    if (isEnter) {
      if (service.onItemSelect) {
        service.onItemSelect(item, state);
      }
    } else if (isEscape) {
      state.set({ ...state, menu: false });
    }
  };

  const options = useMemo(
    () =>
      state.items?.reduce(
        (_options, item, index) => ({
          ..._options,
          [index]: { state, index, last: index === state.items.length - 1 }
        }),
        {}
      ),

    [state]
  );

  return (
    <MenuList data-tui-id="tui-app-search-result" {...menuProps}>
      {state.items?.length > 0 ? (
        state.items.map((item, index) => (
          <MenuItem key={item.id} onKeyDown={event => onKeyDown(event, item)}>
            {service.itemRenderer(item, options[index])}
          </MenuItem>
        ))
      ) : state.items ? (
        <AppListEmpty />
      ) : (
        <MenuItem disabled>
          <Box mt={1} mb={1}>
            <Typography variant="body2">
              <em>{t('app.search.starttyping')}</em>
            </Typography>
          </Box>
        </MenuItem>
      )}
    </MenuList>
  );
};

export default memo(AppSearchResult);
