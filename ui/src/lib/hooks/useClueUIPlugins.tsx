import type { ClueUIPluginContextType } from 'components/app/providers/ClueUIPluginProvider';
import { ClueUIPluginContext } from 'components/app/providers/ClueUIPluginProvider';
import { useContext } from 'react';

const useClueUIPlugins = (): ClueUIPluginContextType => {
  const context = useContext(ClueUIPluginContext);
  if (!context) {
    throw new Error('useClueUIPlugins must be used within a ClueUIPluginProvider');
  }
  return context;
};

export default useClueUIPlugins;
