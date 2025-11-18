import { Delete, MoreVert } from '@mui/icons-material';
import {
  ClickAwayListener,
  IconButton,
  ListItemIcon,
  ListItemText,
  MenuItem,
  MenuList,
  Paper,
  Popper
} from '@mui/material';
import FlexOne from 'commons/addons/flexers/FlexOne';
import { nextSortState, sortIcon } from 'commons/addons/search';
import TuiSearchTerms, { TuiSearchDirection } from 'commons/addons/search/models/TuiSearchTerms';
import useSpacing from 'commons/addons/styles/useSpacing';
import { memo, MouseEvent, useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { TuiTableColumn } from '.';

const TuiTableHeader = ({
  width,
  column,
  sorters,
  onClick
}: {
  width: number;
  column: TuiTableColumn;
  sorters?: TuiSearchTerms;
  onClick?: (model: TuiSearchTerms) => void;
}) => {
  const popperAnchor = useRef();
  const { t } = useTranslation();
  const s1 = useSpacing(1);
  const sorter = sorters ? sorters.findByColumn(column.column) : null;
  const sorterIndex = sorters ? sorters.findIndexByColumn(column.column) : -1;
  const [showMenu, setShowMenu] = useState<boolean>(false);

  const onHeaderClick = useCallback(() => {
    if (onClick) {
      if (sorter) {
        sorter.value = nextSortState(sorter.value);
      } else {
        sorters.orderBy(column.column, 'asc');
      }
      onClick(sorters.rebuild());
    }
  }, [column, sorter, sorters, onClick]);

  const onMenuButtonClick = event => {
    event.stopPropagation();
    setShowMenu(!showMenu);
  };

  const onMenuItemClick = useCallback(
    (event: MouseEvent<HTMLElement>) => {
      event.stopPropagation();
      const action = event.currentTarget.dataset.sortaction;
      if (action === 'remove') {
        onClick(sorters.remove(sorter).rebuild());
      } else if (sorter) {
        sorter.value = action;
        onClick(sorters.rebuild());
      } else {
        onClick(sorters.orderBy(column.column, action as TuiSearchDirection).rebuild());
      }
    },
    [column, sorter, sorters, onClick]
  );

  return (
    <div
      className={`tui-table-header ${column.sortable && onClick ? 'tui-table-header-hover' : ''} ${
        showMenu ? 'tui-table-header-active' : ''
      }`}
      style={{ minWidth: width }}
      onClick={!showMenu ? onHeaderClick : null}
    >
      {sorter && sortIcon(sorter.value, sorters.count() > 1 ? sorterIndex : -1)}
      {sorter && <div style={{ margin: s1 }} />}
      <div>{column.i18nKey ? t(column.i18nKey) : column.label}</div>

      {column.sortable && onClick && (
        <>
          <FlexOne />
          <IconButton
            ref={popperAnchor}
            size="small"
            className={!showMenu ? 'tui-table-header-menu-btn' : null}
            onClick={onMenuButtonClick}
          >
            <MoreVert />
          </IconButton>
          <ClickAwayListener onClickAway={() => setShowMenu(false)}>
            <Popper anchorEl={popperAnchor.current} open={showMenu} placement="bottom-end" disablePortal>
              <Paper elevation={1} className="tui-table-header-menu">
                <MenuList disablePadding>
                  <MenuItem
                    disabled={sorter && sorter.value === 'unset'}
                    data-sortaction="unset"
                    onClick={onMenuItemClick}
                  >
                    <ListItemIcon>{sortIcon('unset')}</ListItemIcon>
                    <ListItemText>{t('tui.list.sorters.unsort')}</ListItemText>
                  </MenuItem>
                  <MenuItem disabled={sorter && sorter.value === 'asc'} data-sortaction="asc" onClick={onMenuItemClick}>
                    <ListItemIcon>{sortIcon('asc')}</ListItemIcon>
                    <ListItemText>{t('tui.list.sorters.asc')}</ListItemText>
                  </MenuItem>
                  <MenuItem
                    disabled={sorter && sorter.value === 'desc'}
                    data-sortaction="desc"
                    onClick={onMenuItemClick}
                  >
                    <ListItemIcon>{sortIcon('desc')}</ListItemIcon>
                    <ListItemText>{t('tui.list.sorters.desc')} </ListItemText>
                  </MenuItem>
                  <MenuItem disabled={!sorter} data-sortaction="remove" onClick={onMenuItemClick}>
                    <ListItemIcon>
                      <Delete />
                    </ListItemIcon>
                    <ListItemText>{t('tui.list.sorters.remove')}</ListItemText>
                  </MenuItem>
                </MenuList>
              </Paper>
            </Popper>
          </ClickAwayListener>
        </>
      )}
    </div>
  );
};

export default memo(TuiTableHeader);
