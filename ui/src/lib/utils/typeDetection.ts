import type { TypesDetectionV2Response } from 'lib/types/lookup';

export type TypeDetector = [type: string, regex: RegExp];

/** Compile in descending priority order, retaining registry order for ties. */
export const compileTypeDetectors = (definitions: TypesDetectionV2Response): TypeDetector[] => {
  return Object.entries(definitions)
    .sort(([, left], [, right]) => (right.priority ?? 0) - (left.priority ?? 0))
    .flatMap(([type, definition]) =>
      definition.regex === null
        ? []
        : [[type, new RegExp(definition.regex, definition.case_sensitive ? '' : 'i')] as TypeDetector]
    );
};

/** Match without altering the input or retrying case-sensitive patterns in lowercase. */
export const detectType = (value: string, detectors: TypeDetector[]): string | null => {
  return value ? (detectors.find(([, regex]) => regex.test(value))?.[0] ?? null) : null;
};
