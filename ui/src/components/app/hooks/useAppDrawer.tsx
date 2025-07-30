import { useContext } from 'react';
import { AppDrawerContext } from '../providers/AppDrawerProvider';

export default function useAppDrawer() {
  return useContext(AppDrawerContext);
}
