import { ClueConfigContext } from 'lib/hooks/ClueConfigProvider';
import { useContext } from 'react';

export default function useClueConfig() {
  return useContext(ClueConfigContext);
}
