import type { Annotation, WithExtra } from 'lib/types/lookup';
import uniqBy from 'lodash-es/uniqBy';
import { useContext, useEffect, useMemo, useState } from 'react';
import { ClueDatabaseContext } from './ClueDatabaseContext';
import { useClueEnrichSelector } from './selectors';

interface AnnotationOptions {
  skipEnrichment?: boolean;
}

/**
 * Custom hook to manage and retrieve annotations for a specific type, value, and classification.
 *
 * This hook interacts with the Clue database to:
 * 1. Track the loading state of annotations.
 * 2. Automatically queue enrichment tasks if required.
 * 3. Retrieve and update annotations in real-time using RxDB observables.
 *
 * @param type - The type of the annotation (e.g., entity type).
 * @param value - The value to search for annotations.
 * @param classification - The classification of the annotation.
 * @param options - Additional options:
 *   - skipEnrichment: If true, skips the enrichment process.
 * @returns A tuple containing:
 *   - An array of annotations with extra metadata.
 *   - A boolean indicating the loading state.
 */
const useAnnotations = (
  type: string,
  value: string,
  _classification?: string,
  { skipEnrichment }: AnnotationOptions = { skipEnrichment: false }
): [WithExtra<Annotation>[], boolean] => {
  const database = useContext(ClueDatabaseContext);

  const defaultClassification = useClueEnrichSelector(ctx => ctx.defaultClassification);
  const enrichReady = useClueEnrichSelector(ctx => ctx.ready);
  const availableSources = useClueEnrichSelector(ctx => ctx.availableSources);
  const queueEnrich = useClueEnrichSelector(state => state.queueEnrich);

  const classification = useMemo(
    () => _classification ?? defaultClassification,
    [_classification, defaultClassification]
  );

  // Local state to track loading status and annotations
  const [loading, setLoading] = useState(false);
  const [annotations, setAnnotations] = useState<WithExtra<Annotation>[]>([]);
  // Memoized readiness check to ensure all required parameters are valid
  const ready = useMemo(
    () => enrichReady && !!type && !!value && !!classification,
    [classification, enrichReady, type, value]
  );

  useEffect(() => {
    if (!ready || !database?.status) {
      return;
    }

    // Monitor the status database for in-progress requests
    const observable = database.status
      .count({ selector: { type, value, classification, status: 'in-progress' } })
      .$.subscribe(_count => setLoading(_count > 0));

    return () => {
      observable?.unsubscribe();
    };
  }, [classification, database, ready, type, value]);

  useEffect(() => {
    if (skipEnrichment || availableSources.length < 1 || !ready) {
      return;
    }

    queueEnrich(type, value, classification);
  }, [availableSources.length, classification, queueEnrich, ready, skipEnrichment, type, value]);

  useEffect(() => {
    // Fetch and update annotations in real-time using RxDB observables
    if (!ready) {
      return;
    }

    const observable = database.selectors
      .find({
        selector: {
          // Use regex instead of exact value for case-insensitivity
          value: { $regex: `^${value}$`, $options: 'i' }
        }
      })
      .$.subscribe(result =>
        setAnnotations(
          uniqBy(
            result.flatMap(entry => entry.getAnnotations()),
            JSON.stringify
          )
        )
      );

    // Cleanup subscription to prevent memory leaks
    return () => {
      try {
        observable.unsubscribe();
      } catch (e) {
        // eslint-disable-next-line no-console
        console.warn(e);
      }
    };
  }, [database, ready, value]);

  return [annotations, loading];
};

export default useAnnotations;
