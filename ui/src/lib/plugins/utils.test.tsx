import { describe, expect, it } from 'vitest';
import { validateJsonData } from './utils';

describe('validateJsonData', () => {
  it('should return the same object when input is already an object', () => {
    const input = { key: 'value', nested: { count: 1 } };

    const result = validateJsonData(input);

    expect(result).toBe(input);
  });

  it('should parse a valid JSON string object', () => {
    const result = validateJsonData('{"name":"clue","enabled":true}');

    expect(result).toEqual({ name: 'clue', enabled: true });
  });

  it('should throw an error when JSON string cannot be parsed', () => {
    expect(() => validateJsonData('{invalid-json}')).toThrowError(/Failed to parse JSON string:/);
  });

  it.each([
    ['number', 123],
    ['boolean', false],
    ['null', null],
    ['undefined', undefined]
  ])('should throw for non-object input: %s', (_label, input) => {
    expect(() => validateJsonData(input)).toThrowError(
      /Input must be a JSON object or a JSON object encoded as a string\./
    );
  });

  it('should allow arrays because they are objects at runtime', () => {
    const input = ['a', 'b', 'c'];

    const result = validateJsonData(input);

    expect(result).toBe(input);
  });
});
