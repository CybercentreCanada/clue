import type { Dispatch, FC, PropsWithChildren, SetStateAction } from 'react';
import { useMemo, useState } from 'react';
import { createContext } from 'use-context-selector';
import useClueEnrichSelector from './selectors';

export type ClueGroupContextProps = {
  type: string;
  classification?: string;
};

export type ClueGroupContextType = {
  type: string;
  classification: string;
  values: any[];
  setValues: Dispatch<SetStateAction<any[]>>;
};

export const ClueGroupContext = createContext<ClueGroupContextType>(null);

export const ClueGroupProvider: FC<PropsWithChildren<ClueGroupContextProps>> = ({ children, type, classification }) => {
  const defaultClassification = useClueEnrichSelector(ctx => ctx.defaultClassification);

  const [values, setValues] = useState<any[]>([]);

  const context = useMemo(
    () => ({
      type,
      values,
      setValues,
      classification: classification ?? defaultClassification
    }),
    [classification, defaultClassification, type, values]
  );

  return <ClueGroupContext.Provider value={context}>{children}</ClueGroupContext.Provider>;
};
