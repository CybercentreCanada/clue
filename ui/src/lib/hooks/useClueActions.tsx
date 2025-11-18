import { useContext } from 'use-context-selector';
import type { ClueActionContextType } from './ClueActionContext';
import { ClueActionContext } from './ClueActionContext';

const useClueActions = (): ClueActionContextType => {
  return useContext(ClueActionContext);
};

export default useClueActions;
