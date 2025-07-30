import { AppLeftNavContext } from 'commons/components/app/providers/AppLeftNavProvider';
import { useContext } from 'react';

export default function useAppLeftNav() {
  return useContext(AppLeftNavContext);
}
