import { useContext } from 'react';
import { TuiFormContext } from '../TuiFormProvider';

export default function useTuiForm() {
  return useContext(TuiFormContext);
}
