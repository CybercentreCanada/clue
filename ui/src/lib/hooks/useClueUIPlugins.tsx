import { useContext } from 'react';
import type { ClueUIPluginContextType } from './ClueUIPluginContext';
import { ClueUIPluginContext } from './ClueUIPluginContext';

const useClueUIPlugins = (): ClueUIPluginContextType => {
  const context = useContext(ClueUIPluginContext);
  if (!context) {
    throw new Error('useClueUIPlugins must be used within a ClueUIPluginProvider');
  }
  return context;
};

export default useClueUIPlugins;
