import { useContext } from 'react';
import { VSBoxContext } from '../VSBox';

export default function useVsBox() {
  return useContext(VSBoxContext);
}
