import {
  ClickAwayListener,
  List,
  ListItemButton,
  ListItemButtonProps,
  Paper,
  PaperProps,
  Popper,
  PopperPlacementType
} from '@mui/material';
import { FC, useRef, useState } from 'react';
import TuiIconButton, { TuiIconButtonProps } from './TuiIconButton';

type TuiIconButtonSelectProps = {
  items: ListItemButtonProps[];
  placement?: PopperPlacementType;
  OptionsPaperProps?: PaperProps;
} & Omit<TuiIconButtonProps, 'onChange'>;

export const TuiIconButtonMenu: FC<TuiIconButtonSelectProps> = ({
  items,
  placement = 'auto-end',
  OptionsPaperProps,
  ...chipProps
}) => {
  const anchorRef = useRef<HTMLDivElement>();
  const [open, setOpen] = useState<boolean>(false);

  return (
    <ClickAwayListener onClickAway={() => setOpen(false)}>
      <div ref={anchorRef}>
        <TuiIconButton {...chipProps} onClick={() => setOpen(!open)} />
        <Popper anchorEl={anchorRef?.current} open={open} placement={placement} style={{ zIndex: 3000 }}>
          <Paper sx={{ maxHeight: 400, overflow: 'auto' }} {...OptionsPaperProps}>
            <List dense sx={{ paddingTop: 0, paddingBottom: 0 }}>
              {items.map(iProps => (
                <ListItemButton {...iProps} />
              ))}
            </List>
          </Paper>
        </Popper>
      </div>
    </ClickAwayListener>
  );
};
