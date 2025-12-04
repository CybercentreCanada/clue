import type { ClueActionContextType } from 'lib/hooks/ClueActionContext';
import { ClueActionContext } from 'lib/hooks/ClueActionContext';
import { useContext } from 'use-context-selector';

const useClueActions = (): ClueActionContextType => {
  return useContext(ClueActionContext);
};

export default useClueActions;
