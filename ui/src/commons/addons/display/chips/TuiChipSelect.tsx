import { ArrowDropDown, ArrowDropUp } from '@mui/icons-material';
import {
  Chip,
  ChipProps,
  ClickAwayListener,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  PaperProps,
  Popper
} from '@mui/material';
import { memo, useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

export type ChipSelectOption<T = any> = {
  value: T;
  i18nKey?: string;
  label?: string;
};

type ChipSelectProps<T = any> = Omit<ChipProps, 'onChange' | 'onClick' | 'onDelete'> & {
  options: ChipSelectOption[];
  value: any;
  optionEqual?: (seletion: T, option: T) => void;
  onChange: (selection: ChipSelectOption) => void;
  OptionsPaperProps?: PaperProps;
};

const TuiChipSelect = ({ options, value, OptionsPaperProps, optionEqual, onChange, ...chipProps }: ChipSelectProps) => {
  const { t } = useTranslation();
  const ref = useRef<HTMLDivElement>();
  const [open, setOpen] = useState<boolean>(false);
  const selectedOption = options.find(o => (optionEqual ? optionEqual(value, o.value) : o.value === value));

  const onOptionClick = useCallback(
    (selection: ChipSelectOption) => {
      onChange(selection);
      setOpen(false);
    },
    [onChange]
  );

  return (
    <ClickAwayListener onClickAway={() => setOpen(false)}>
      <div ref={ref} style={{ position: 'relative', display: 'inline-block' }}>
        <Chip
          {...chipProps}
          onClick={() => setOpen(!open)}
          label={selectedOption && (selectedOption.i18nKey ? t(selectedOption.i18nKey) : selectedOption.label)}
          deleteIcon={open ? <ArrowDropUp /> : <ArrowDropDown />}
          onDelete={() => setOpen(!open)}
        />
        <Popper anchorEl={ref?.current} open={open} placement="bottom-start" style={{ zIndex: 3000 }}>
          <Paper sx={{ maxHeight: 400, overflow: 'auto' }} {...OptionsPaperProps}>
            <List dense sx={{ paddingTop: 0, paddingBottom: 0 }}>
              {options.map(o => {
                const label = o.i18nKey ? t(o.i18nKey) : o.label;
                return (
                  <ListItemButton key={label} onClick={() => onOptionClick(o)}>
                    <ListItemText>{label}</ListItemText>
                  </ListItemButton>
                );
              })}
            </List>
          </Paper>
        </Popper>
      </div>
    </ClickAwayListener>
  );
};

export default memo(TuiChipSelect);
