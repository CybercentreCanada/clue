import { useContext } from 'use-context-selector';
import { ClueEnrichContext } from './ClueEnrichContext';
import type { ClueEnrichContextType } from './ClueEnrichContextType';

const useClue = (): ClueEnrichContextType => {
  return useContext(ClueEnrichContext);
};

export default useClue;
