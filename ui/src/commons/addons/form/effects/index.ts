import { initFormField, TuiForm } from '../TuiFormProvider';

export function mandatory(...fieldId: string[]) {
  return (form: TuiForm) => {
    fieldId.forEach(id => {
      if (!form[id]) {
        form[id] = initFormField({ id });
      }
      const field = form[id];
      field.invalid = !field.value;
    });

    return form;
  };
}

export function mandatoryIfOtherNotEmpty(fieldId: string, ...otherId: string[]) {
  return (form: TuiForm) => {
    if (!form[fieldId]) {
      form[fieldId] = initFormField({ id: fieldId });
    }
    const field = form[fieldId];
    const others = Object.values(form).filter(f => otherId.some(_fid => f.id === _fid));
    field.invalid = !field.value && others.every(of => !!of.value);
    return form;
  };
}

export function disableIfOtherEmpty(fieldId: string, ...otherId: string[]) {
  return (form: TuiForm) => {
    if (!form[fieldId]) {
      form[fieldId] = initFormField({ id: fieldId });
    }
    const field = form[fieldId];
    const others = Object.values(form).filter(f => otherId.some(_fid => f.id === _fid));
    field.disabled = others.every(of => !of.value);
    return form;
  };
}
