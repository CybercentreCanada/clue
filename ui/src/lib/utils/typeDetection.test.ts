import type { TypesDetectionV2Response } from 'lib/types/lookup';
import { describe, expect, it } from 'vitest';
import { compileTypeDetectors, detectType } from './typeDetection';

describe('type detection', () => {
  it('uses the highest priority rather than the first matching definition', () => {
    const detectors = compileTypeDetectors({
      fallback: { regex: '^.+$', case_sensitive: true },
      specific: { regex: '^ticket-\\d+$', case_sensitive: true, priority: 100 }
    });
    expect(detectType('ticket-123', detectors)).toBe('specific');
  });

  it('prefers IPv4 over an overlapping URL pattern', () => {
    const detectors = compileTypeDetectors({
      url: { regex: '^(?:https?://)?(?:[0-9]{1,3}\\.){3}[0-9]{1,3}(?:/\\S*)?$', case_sensitive: true },
      ipv4: { regex: '^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$', case_sensitive: true, priority: 10 }
    });
    expect(detectType('127.0.0.1', detectors)).toBe('ipv4');
    expect(detectType('http://127.0.0.1/path', detectors)).toBe('url');
  });

  it('applies the IPv6 priority as well', () => {
    const detectors = compileTypeDetectors({
      custom: { regex: '^.+$', case_sensitive: true },
      ipv6: { regex: '^[0-9a-fA-F:]+$', case_sensitive: true, priority: 10 }
    });
    expect(detectType('2001:DB8::1', detectors)).toBe('ipv6');
  });

  it('preserves registry order on equal priorities, including MD5 and JA3', () => {
    const regex = '^[a-fA-F0-9]{32}$';
    const detectors = compileTypeDetectors({
      md5: { regex, case_sensitive: true },
      ja3: { regex, case_sensitive: true, priority: 0 }
    });
    expect(detectType('a'.repeat(32), detectors)).toBe('md5');
  });

  it('preserves insertion order rather than sorting type names for ties', () => {
    const detectors = compileTypeDetectors({
      zebra: { regex: '^match$', case_sensitive: true, priority: 5 },
      alpha: { regex: '^match$', case_sensitive: true, priority: 5 }
    });
    expect(detectType('match', detectors)).toBe('zebra');
  });

  it('defaults omitted priorities to zero and permits negative priorities', () => {
    const detectors = compileTypeDetectors({
      fallback: { regex: '^.+$', case_sensitive: true, priority: -10 },
      default: { regex: '^match$', case_sensitive: true }
    });
    expect(detectType('match', detectors)).toBe('default');
    expect(detectType('other', detectors)).toBe('fallback');
  });

  it('matches case-insensitive definitions using the i flag', () => {
    const detectors = compileTypeDetectors({ domain: { regex: '^[a-z]+\\.com$', case_sensitive: false } });
    expect(detectors[0][1].flags).toBe('i');
    expect(detectType('EXAMPLE.COM', detectors)).toBe('domain');
    expect(detectType('example.com', detectors)).toBe('domain');
  });

  it('never retries a case-sensitive pattern against lowercased input', () => {
    const detectors = compileTypeDetectors({ custom: { regex: '^lowercase$', case_sensitive: true } });
    expect(detectors[0][1].flags).toBe('');
    expect(detectType('lowercase', detectors)).toBe('custom');
    expect(detectType('LOWERCASE', detectors)).toBe(null);
  });

  it('keeps case-sensitive uppercase-only patterns working', () => {
    const detectors = compileTypeDetectors({ email_path: { regex: '^[A-Z]+_EMAIL://.*', case_sensitive: true } });
    expect(detectType('USER_EMAIL://MixedCase', detectors)).toBe('email_path');
    expect(detectType('user_email://MixedCase', detectors)).toBe(null);
  });

  it('lets a higher-priority case-insensitive match beat an exact-case match', () => {
    const detectors = compileTypeDetectors({
      exact: { regex: '^MATCH$', case_sensitive: true },
      preferred: { regex: '^match$', case_sensitive: false, priority: 10 }
    });
    expect(detectType('MATCH', detectors)).toBe('preferred');
    expect(detectType('MATCH', detectors)).toBe('preferred');
  });

  it('skips null regexes regardless of priority', () => {
    const detectors = compileTypeDetectors({
      explicit: { regex: null, case_sensitive: false, priority: 100 },
      custom: { regex: '^match$', case_sensitive: true }
    });
    expect(detectors.map(([type]) => type)).toEqual(['custom']);
    expect(detectType('match', detectors)).toBe('custom');
  });

  it('returns null for empty, missing, or unmatched inputs and empty definitions', () => {
    const definitions: TypesDetectionV2Response = { custom: { regex: '^match$', case_sensitive: true } };
    const detectors = compileTypeDetectors(definitions);
    expect(detectType('', detectors)).toBe(null);
    expect(detectType(null, detectors)).toBe(null);
    expect(detectType(undefined, detectors)).toBe(null);
    expect(detectType('other', detectors)).toBe(null);
    expect(detectType('match', compileTypeDetectors({}))).toBe(null);
  });
});
