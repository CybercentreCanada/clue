import buildDatabase from 'lib/database';
import type { ClueDatabase } from 'lib/database/types';
import type { FC, PropsWithChildren } from 'react';
import { createContext, useEffect, useState } from 'react';

export interface ClueDatabaseContextProps {
  database?: ClueDatabase;
}

export type ClueDatabaseContextType = ClueDatabase;

export const ClueDatabaseContext = createContext<ClueDatabaseContextType>(null);

export const ClueDatabaseProvider: FC<PropsWithChildren<ClueDatabaseContextProps>> = ({
  children,
  database: _database
}) => {
  const [database, setDatabase] = useState<ClueDatabase>();

  useEffect(() => {
    if (_database) {
      setDatabase(_database);
    } else {
      buildDatabase().then(setDatabase);
    }
  }, [_database]);

  return <ClueDatabaseContext.Provider value={database}>{children}</ClueDatabaseContext.Provider>;
};
