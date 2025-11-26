import { useContext, useEffect, useState } from 'react';
import { ClueDatabaseContext } from './ClueDatabaseContext';
import { useClueEnrichSelector } from './selectors';

/**
 * Custom hook that retrieves error records from the database for a given value.
 *
 * This hook monitors the database for records that match the provided value and have
 * an error field present. It returns an array of error objects containing the source
 * and message for each error found.
 *
 * @param value - The value to search for in the database records
 * @returns An array of error objects, each containing:
 *   - source: The source identifier where the error originated
 *   - message: The error message content
 */
const useErrors = (value: string): { source: string; message: string }[] => {
  const database = useContext(ClueDatabaseContext);
  const ready = useClueEnrichSelector(ctx => ctx.ready);

  // Local state to store the array of error records
  const [errors, setErrors] = useState<{ source: string; message: string }[]>([]);

  useEffect(() => {
    if (!ready || !value) {
      return;
    }

    // Create a reactive query to find records that:
    // 1. Match the provided value
    // 2. Have an error field present (using MongoDB-style $exists operator)
    const observable = database.selectors
      .find({ selector: { value: value, error: { $exists: true } } })
      .$.subscribe(records =>
        // Transform database records into simplified error objects
        setErrors(
          records.map(record => ({
            source: record.source,
            message: record.error
          }))
        )
      );

    return () => {
      try {
        observable.unsubscribe();
      } catch (e) {
        // Log warning if unsubscription fails (shouldn't normally happen)
        // eslint-disable-next-line no-console
        console.warn(e);
      }
    };
  }, [database, ready, value]);

  return errors;
};

export default useErrors;
