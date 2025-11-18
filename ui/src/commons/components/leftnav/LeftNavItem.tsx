import { ListItem, ListItemButton, ListItemIcon, ListItemText, Tooltip } from '@mui/material';
import useAppConfigs from 'commons/components/app/hooks/useAppConfigs';
import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { AppLeftNavItem } from '../app/AppConfigs';
import useAppLeftNav from '../app/hooks/useAppLeftNav';
import useAppUser from '../app/hooks/useAppUser';

type LeftNavItemProps = {
  item: AppLeftNavItem;
  onClick: () => void;
};

const LeftNavItem = ({ item, onClick }: LeftNavItemProps) => {
  const { t } = useTranslation();
  const { preferences } = useAppConfigs();
  const user = useAppUser();
  const leftnav = useAppLeftNav();
  const { text, icon, i18nKey, nested, route, render, userPropValidators } = item;
  const label = i18nKey ? t(i18nKey) : text;
  return user.validateProps(userPropValidators) ? (
    render ? (
      <ListItem disablePadding>{render(leftnav.open)}</ListItem>
    ) : (
      <Tooltip title={!leftnav.open && !nested ? label : ''} aria-label={label} placement="right">
        <ListItemButton
          component={route ? Link : null}
          to={route}
          dense={!!nested}
          key={text}
          onClick={onClick ? onClick : null}
          sx={{
            ...(nested && { paddingLeft: 4 })
          }}
        >
          {((icon && !nested) || (!preferences.leftnav.hideNestedIcons && icon && nested)) && (
            <ListItemIcon>{icon}</ListItemIcon>
          )}
          <ListItemText primary={label} />
        </ListItemButton>
      </Tooltip>
    )
  ) : null;
};

export default memo(LeftNavItem);
