import ExpandLess from '@mui/icons-material/ExpandLess';
import ExpandMore from '@mui/icons-material/ExpandMore';
import { Collapse, List, ListItemButton, ListItemIcon, ListItemText, Popover, Tooltip } from '@mui/material';
import LeftNavItem from 'commons/components/leftnav/LeftNavItem';
import { memo, useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AppLeftNavGroup } from '../app/AppConfigs';
import useAppLeftNav from '../app/hooks/useAppLeftNav';
import useAppUser from '../app/hooks/useAppUser';

interface LeftNavGroupProps {
  group: AppLeftNavGroup;
  onItemClick: () => void;
}

const LeftNavGroup = ({ group, onItemClick }: LeftNavGroupProps) => {
  const user = useAppUser();
  const leftnav = useAppLeftNav();
  const [popoverTarget, setPopoverTarget] = useState<(EventTarget & Element) | undefined>();
  const [collapseOpen, setCollapseOpen] = useState(false);

  const handleClick = useCallback(
    (event: React.MouseEvent) => {
      if (leftnav.open) {
        setCollapseOpen(!collapseOpen);
      } else {
        setPopoverTarget(event ? event.currentTarget : undefined);
      }
    },
    [leftnav.open, collapseOpen]
  );

  const onClosePopover = useCallback(() => setPopoverTarget(undefined), []);

  useEffect(() => {
    if (!leftnav.open && collapseOpen) {
      setCollapseOpen(false);
    }
  }, [leftnav.open, collapseOpen]);

  return user.validateProps(group.userPropValidators) ? (
    <div>
      <GroupListItem group={group} leftNavOpen={leftnav.open} collapsed={collapseOpen} onClick={handleClick} />
      <Collapse in={collapseOpen} timeout="auto" unmountOnExit>
        <List component="div" disablePadding>
          {group.items.map(i => (
            <LeftNavItem key={i.id} item={i} onClick={onItemClick} />
          ))}
        </List>
      </Collapse>
      <Popover
        open={!!popoverTarget}
        onClose={onClosePopover}
        onClick={onClosePopover}
        anchorEl={popoverTarget}
        anchorOrigin={{
          vertical: 'top',
          horizontal: 'right'
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'left'
        }}
      >
        <List disablePadding>
          {group.items.map(i => (
            <LeftNavItem key={i.id} item={i} onClick={onItemClick} />
          ))}
        </List>
      </Popover>
    </div>
  ) : null;
};

const GroupListItem = memo(
  ({
    group,
    leftNavOpen,
    collapsed,
    onClick
  }: {
    group: AppLeftNavGroup;
    leftNavOpen: boolean;
    collapsed: boolean;
    onClick: (event: React.MouseEvent) => void;
  }) => {
    const { t } = useTranslation();
    const title = group.i18nKey ? t(group.i18nKey) : group.title;
    return (
      <Tooltip title={!leftNavOpen ? title : ''} aria-label={title} placement="right">
        <ListItemButton key={group.id} onClick={onClick}>
          <ListItemIcon>{group.icon}</ListItemIcon>
          <ListItemText primary={title} />
          {collapsed ? <ExpandLess color="action" /> : <ExpandMore color="action" />}
        </ListItemButton>
      </Tooltip>
    );
  }
);

export default memo(LeftNavGroup);
