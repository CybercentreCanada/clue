import buildDatabase from 'lib/database';
import type { ClueDatabase, DatabaseConfig } from 'lib/database/types';
import type { FC, PropsWithChildren } from 'react';
import { createContext, useEffect, useState } from 'react';

export interface ClueDatabaseContextProps {
  database?: ClueDatabase;
  databaseConfig?: DatabaseConfig;
}

export type ClueDatabaseContextType = ClueDatabase;

export const ClueDatabaseContext = createContext<ClueDatabaseContextType>(null);

export const ClueDatabaseProvider: FC<PropsWithChildren<ClueDatabaseContextProps>> = ({
  children,
  database: _database,
  databaseConfig
}) => {
  const [database, setDatabase] = useState<ClueDatabase>();

  useEffect(() => {
    if (_database) {
      setDatabase(_database);
    } else {
      buildDatabase(databaseConfig).then(setDatabase);
    }
  }, [_database, databaseConfig]);

  return <ClueDatabaseContext.Provider value={database}>{children}</ClueDatabaseContext.Provider>;
};
