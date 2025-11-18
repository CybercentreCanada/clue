import { Autocomplete, AutocompleteChangeReason, TextField } from '@mui/material';
import { SyntheticEvent, useCallback } from 'react';
import { TuiFormField } from '../TuiFormProvider';

export type TuiFormFieldSelectorOption = { label?: string; type?: string; field: TuiFormField };

type TuiFormFieldSelectorProps = {
  label?: string;
  selections: TuiFormFieldSelectorOption[];
  options: TuiFormFieldSelectorOption[];
  onChange: (selections: TuiFormFieldSelectorOption[]) => void;
};

export default function TuiFormFieldSelector({ label, selections, options, onChange }: TuiFormFieldSelectorProps) {
  const _onChange = useCallback(
    (event: SyntheticEvent<Element, Event>, value: TuiFormFieldSelectorOption[], reason: AutocompleteChangeReason) => {
      onChange(value);
    },
    [onChange]
  );

  return (
    <Autocomplete
      multiple
      disableCloseOnSelect
      value={selections}
      options={options}
      getOptionLabel={(option: TuiFormFieldSelectorOption) => option.label}
      renderInput={params => <TextField {...params} label={label} />}
      onChange={_onChange}
    />
  );
}
