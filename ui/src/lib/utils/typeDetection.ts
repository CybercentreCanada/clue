import type { TypesDetectionV2Response } from 'lib/types/lookup';

export type TypeDetector = [type: string, regex: RegExp];

/** Stable sorting preserves registry order for equal priorities. */
export const compileTypeDetectors = (definitions: TypesDetectionV2Response): TypeDetector[] =>
  Object.entries(definitions)
    .sort(([, left], [, right]) => (right.priority ?? 0) - (left.priority ?? 0))
    .flatMap(([type, definition]): TypeDetector[] =>
      definition.regex === null ? [] : [[type, new RegExp(definition.regex, definition.case_sensitive ? '' : 'i')]]
    );

export const detectType = (value: string, detectors: TypeDetector[]): string | null =>
  value ? (detectors.find(([, regex]) => regex.test(value))?.[0] ?? null) : null;
