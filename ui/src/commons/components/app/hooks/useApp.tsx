import { AppContext } from 'commons/components/app/AppProvider';
import { useContext } from 'react';

export default function useApp() {
  return useContext(AppContext);
}
