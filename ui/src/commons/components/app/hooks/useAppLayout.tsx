import { AppLayoutContext } from 'commons/components/app/providers/AppLayoutProvider';
import { useContext } from 'react';

export default function useAppLayout() {
  return useContext(AppLayoutContext);
}
