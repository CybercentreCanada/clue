import { ArrowDropDown, ArrowDropUp } from '@mui/icons-material';
import {
  Chip,
  ChipProps,
  ClickAwayListener,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  Popper
} from '@mui/material';
import { FC, ReactElement, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { TuiLink, TuiLinkProps } from '../links/TuiLink';

export type TuiChipMenuOption = {
  id: string;
  label?: string;
  i18nKey?: string;
  icon?: ReactElement;
  link?: TuiLinkProps;
  element?: ReactElement;
  onClick?: () => void;
};

export type TuiChipMenuProps = Omit<ChipProps, 'label'> & {
  title: string | ReactElement;
  options: TuiChipMenuOption[];
};

export const TuiChipMenu: FC<TuiChipMenuProps> = ({ title, options, ...chipProps }) => {
  const anchorRef = useRef<HTMLDivElement>();
  const { t } = useTranslation();
  const [open, setOpen] = useState<boolean>(false);

  return (
    <ClickAwayListener onClickAway={() => setOpen(false)}>
      <div ref={anchorRef} style={{ position: 'relative' }}>
        <Chip
          {...chipProps}
          label={title}
          onClick={options?.length > 0 && (() => setOpen(!open))}
          deleteIcon={options?.length > 0 && (open ? <ArrowDropUp /> : <ArrowDropDown />)}
          onDelete={options?.length > 0 && (() => setOpen(!open))}
        />
        <Popper
          anchorEl={anchorRef?.current}
          open={open && options.length > 0}
          placement="bottom"
          style={{ zIndex: 3000 }}
        >
          <Paper>
            <List dense sx={{ paddingTop: 0, paddingBottom: 0 }}>
              {options.map(o => {
                if (o.element) {
                  return o.element;
                }
                const label = o.i18nKey ? t(o.i18nKey) : o.label;
                return (
                  <TuiLink {...o.link} key={o.id}>
                    <ListItemButton key={label} onClick={o.onClick}>
                      {o.icon && <ListItemIcon>{o.icon}</ListItemIcon>}
                      <ListItemText>{label}</ListItemText>
                    </ListItemButton>
                  </TuiLink>
                );
              })}
            </List>
          </Paper>
        </Popper>
      </div>
    </ClickAwayListener>
  );
};
