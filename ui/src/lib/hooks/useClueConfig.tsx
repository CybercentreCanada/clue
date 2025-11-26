import { ClueConfigContext } from 'lib/hooks/ClueConfigProvider';
import { useContext } from 'react';

const useClueConfig = () => {
  return useContext(ClueConfigContext);
};

export default useClueConfig;
