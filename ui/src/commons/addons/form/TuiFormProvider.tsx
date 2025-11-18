import { createContext, ReactNode, useCallback, useEffect, useMemo, useState } from 'react';

const EMPTY_LIST = [];

export type TuiFormEffect = (form?: TuiForm) => TuiForm;

export type TuiFormField = {
  id: string;
  value?: any;
  original?: any;
  disabled?: boolean;
  invalid?: boolean;
  changed?: boolean;
  init?: boolean;
};

export type TuiForm = {
  [fieldId: string]: TuiFormField;
};

export type TuiFormState = {
  form: TuiForm;
  setForm: (form: TuiForm) => void;
  getField: (fieldId: string) => TuiFormField;
  value: (fieldId: string) => any;
  values: () => { [key: string]: any };
  invalid: (fieldId?: string) => boolean;
  disabled: (fieldId: string) => boolean;
  changed: (fieldId?: string) => boolean;
  reset: () => void;
  rebase: () => void;
  clear: () => void;
  onFieldChange: (fieldId: string, value: any) => void;
};

type TuiFormProps = {
  init?: TuiFormField[];
  effects?: TuiFormEffect[];
  onChange?: (form: TuiForm, field: TuiFormField, newValue: string, oldValue: string) => TuiForm;
  children: ReactNode;
};

export const TuiFormContext = createContext<TuiFormState>({
  form: {},
  setForm: () => null,
  value: () => null,
  values: () => null,
  getField: () => null,
  invalid: () => true,
  disabled: () => false,
  changed: () => false,
  reset: () => null,
  rebase: () => null,
  clear: () => null,
  onFieldChange: () => null
});

export default function TuiFormProvider({ init, effects, onChange, children }: TuiFormProps) {
  // State stuff.
  const [form, setForm] = useState<TuiForm>({});

  // Initialize the form.
  const newForm = useCallback(() => {
    // create object from init fields.
    let firstBorn = (init || []).reduce((prev, f) => ({ ...prev, [f.id]: initFormField(f) }), {}) as TuiForm;

    // apply form effects on init form.
    if (init && effects) {
      firstBorn = effects.reduce((_form, effect) => effect(_form), firstBorn);
    }

    // initialize form state.
    setForm(firstBorn);
  }, [init, effects]);

  // Initialize the form on first render.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(newForm, []);

  // Form field change handler.
  const onFieldChange = useCallback(
    (id: string, value: any) => {
      // re-address the form.
      let updatedForm = { ...form };

      // ensure the form has an entry for the specified field.
      if (!updatedForm[id]) {
        updatedForm[id] = initFormField({ id });
      }

      // cache the old value.
      const oldValue = updatedForm[id].value || null;

      // update the field's value.
      updatedForm[id].value = value;

      // indicate if the value has changed.
      updatedForm[id].changed = value !== updatedForm[id].original;

      // apply form effects.
      updatedForm = (effects || []).reduce((_form, effect) => effect(_form), updatedForm);

      // invoke onchange callback if specified.
      if (onChange) {
        updatedForm = onChange(updatedForm, form[id], form[id].value, oldValue);
      }

      // update state.
      setForm(updatedForm);
    },
    [form, effects, onChange]
  );

  // Get the TuiFormField
  const getField = useCallback((fieldId: string) => form[fieldId], [form]);

  // Get the 'value' property of a TuiFormField.
  const value = useCallback((fieldId: string) => form[fieldId]?.value || '', [form]);

  // Get the 'invalid' property of a TuiFormField.
  // If no fieldId specified, it will assert whether any field is 'invalid'.
  const invalid = useCallback(
    (fieldId?: string) => (fieldId ? form[fieldId]?.invalid : Object.values(form).some(f => f.invalid)),
    [form]
  );

  // Get the 'disabled' property of a TuiFormField.
  const disabled = useCallback((fieldId: string) => form[fieldId]?.disabled, [form]);

  // Get the 'changed' prpoerty of a TuiFormField.
  // If no fieldId specified, it will assert whether any field has 'changed'.
  const changed = useCallback(
    (fieldId?: string) => (fieldId ? form[fieldId]?.changed : Object.values(form).some(f => f.changed)),
    [form]
  );

  // Rebase the form with the current values.
  // 1: resets all 'changed' property to false.
  // 2: sets all 'original' property to the current 'value' property.
  const rebase = useCallback(() => {
    Object.values(form).forEach(f => {
      f.changed = false;
      f.original = f.value;
    });
    setForm({ ...form });
  }, [form]);

  // Set all field values to null.
  const clear = useCallback(() => {
    let _form = form;
    Object.values(form).forEach(f => {
      f.value = null;
      f.changed = f.value !== f.original;
    });
    effects.forEach(effect => (_form = effect(_form)));
    setForm({ ..._form });
  }, [effects, form]);

  // Create simple id/value form with lambdas histerics.
  const values = useCallback(
    () => Object.fromEntries(Object.entries(form).map(([id, field]) => [id, field.value])),
    [form]
  );

  // Memoize Provider's value.
  const state = useMemo(
    () => ({
      form,
      setForm,
      getField,
      value,
      values,
      invalid,
      disabled,
      changed,
      rebase,
      clear,
      onFieldChange,
      reset: newForm
    }),
    [form, getField, value, values, invalid, disabled, changed, newForm, rebase, clear, onFieldChange]
  );
  return <TuiFormContext.Provider value={state}>{children}</TuiFormContext.Provider>;
}

export const initFormField = (field: TuiFormField): TuiFormField => {
  return !field.init
    ? {
        id: field.id,
        value: field.value || null,
        original: field.value || null,
        disabled: false,
        invalid: false,
        changed: false,
        init: true
      }
    : field;
};
