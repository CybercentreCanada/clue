import { useContext } from 'react';
import { AppBarContext } from '../providers/AppBarProvider';

export default function useAppBar() {
  return useContext(AppBarContext);
}
