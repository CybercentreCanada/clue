import type { ApiType } from 'lib/types/config';
import type { FC, PropsWithChildren } from 'react';
import { createContext, useMemo, useState } from 'react';

export type ClueConfigContextProps = { config?: ApiType };

export type ClueConfigContextType = {
  config: ApiType;
  setConfig: (config: ApiType) => void;
};

export const ClueConfigContext = createContext<ClueConfigContextType>(null);

export const ClueConfigProvider: FC<PropsWithChildren<ClueConfigContextProps>> = ({ children, config: _config }) => {
  const [config, setConfig] = useState<ApiType>(
    _config ?? {
      configuration: null,
      c12nDef: null
    }
  );

  const context = useMemo(
    () => ({
      config,
      setConfig
    }),
    [config, setConfig]
  );

  return <ClueConfigContext.Provider value={context}>{children}</ClueConfigContext.Provider>;
};
