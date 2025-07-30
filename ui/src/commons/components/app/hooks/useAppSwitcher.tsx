import { useContext } from 'react';
import { AppSwitcherContext } from '../providers/AppSwitcherProvider';

export default function useAppSwitcher() {
  return useContext(AppSwitcherContext);
}
