/**
 * Creates a hash from the input string.
 * @param value The value to hash.
 * @returns The hashed value.
 */
export function simpleHash(value: string): string {
  let hash = 0;
  for (let i = 0; i < value.length; i++) {
    const char = value.charCodeAt(i);
    hash = (hash << 5) - hash + char;
  }
  return (hash >>> 0).toString(36).padStart(7, '0');
}
