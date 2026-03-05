import buildDatabase from 'lib/database';
import type { ClueDatabase, DatabaseConfig } from 'lib/database/types';
import type { FC, PropsWithChildren } from 'react';
import { createContext, useEffect, useRef, useState } from 'react';

/**
 * Context properties for the Clue Database.
 *
 * Provides access to the Clue database instance, configuration, and authentication utilities
 * for interacting with the Clue API.
 *
 * @property {ClueDatabase} [database] - The Clue database instance. Optional, may be undefined
 * if the database is not yet initialized.
 *
 * @property {DatabaseConfig} [databaseConfig] - Configuration settings for the database connection.
 * Optional, may be undefined if configuration has not been loaded.
 *
 * @example
 * ```tsx
 * const contextProps: ClueDatabaseContextProps = {
 *   database: myDatabaseInstance,
 *   databaseConfig: myConfig
 * };
 * ```
 */
export interface ClueDatabaseContextProps {
  /**
   * The Clue Database instance used for data operations and queries. Optional.
   */
  database?: ClueDatabase;

  /**
   * Configuration settings for the database connection and behavior.
   * Optional - may be undefined if using default database configuration.
   */
  databaseConfig?: DatabaseConfig;

  /**
   * Get an access token for the clue API. Used during replication. Must be a stable reference.
   *
   * @returns An access token valid for use with the clue API.
   */
  getToken?: () => string;
}

export type ClueDatabaseContextType = ClueDatabase;

export const ClueDatabaseContext = createContext<ClueDatabaseContextType>(null);

export const ClueDatabaseProvider: FC<PropsWithChildren<ClueDatabaseContextProps>> = ({
  children,
  database: _database,
  databaseConfig,
  getToken
}) => {
  const [database, setDatabase] = useState<ClueDatabase>();

  // Keep a ref to the latest getToken so the build effect doesn't need it as a
  // reactive dependency. Without this, an inline (unstable) getToken at the
  // call-site would re-trigger the effect on every parent render, building a
  // new database instance each time.
  const getTokenRef = useRef(getToken);
  useEffect(() => {
    getTokenRef.current = getToken;
  }, [getToken]);

  useEffect(() => {
    if (_database) {
      setDatabase(_database);
    }
  }, [_database]);

  useEffect(() => {
    if (!_database) {
      let _createdDatabase: ClueDatabase = null;
      // eslint-disable-next-line no-console
      console.warn('It is heavily suggested to initialize the database outside of the React component tree.');
      buildDatabase(databaseConfig ?? { getToken: getTokenRef.current }).then(_db => {
        _createdDatabase = _db;
        setDatabase(_db);
      });

      return () => {
        _createdDatabase.close();
      };
    }
    // getToken is intentionally omitted from deps — reads from getTokenRef instead.
  }, [_database, databaseConfig]);

  return <ClueDatabaseContext.Provider value={database}>{children}</ClueDatabaseContext.Provider>;
};
