import { describe, expect, it } from 'vitest';
import { compileTypeDetectors, detectType } from './typeDetection';

describe('metadata-based type detection', () => {
  it('uses per-detector flags without changing selector values', () => {
    const detectors = compileTypeDetectors({
      ticket: { regex: '^ticket-\\d+$', case_sensitive: true },
      domain: { regex: '^[a-z]+\\.com$', case_sensitive: false },
      url: { regex: '^(?:https?://)?[a-zA-Z]+\\.com(?:/CaseSensitive)?$', case_sensitive: true },
      email_path: { regex: '^[A-Z]+_EMAIL://.*$', case_sensitive: true }
    });
    expect(detectType('EXAMPLE.COM', detectors)).toBe('domain');
    expect(detectType('ticket-123', detectors)).toBe('ticket');
    expect(detectType('TICKET-123', detectors)).toBeNull();
    expect(detectType('USER_EMAIL://MixedCase', detectors)).toBe('email_path');
    expect(detectType('user_email://MixedCase', detectors)).toBeNull();
    expect(detectType('http://example.com/CaseSensitive', detectors)).toBe('url');
    expect(detectType('http://example.com/casesensitive', detectors)).toBeNull();
    expect(detectors.map(([, regex]) => regex.flags)).toEqual(['', 'i', '', '']);
  });

  it('uses priority before insertion order for overlapping extension and IPv4 patterns', () => {
    const detectors = compileTypeDetectors({
      extension: { regex: '^.+$', case_sensitive: true },
      ipv4: { regex: '^(?:\\d{1,3}\\.){3}\\d{1,3}$', case_sensitive: true, priority: 10 }
    });
    expect(detectType('192.0.2.1', detectors)).toBe('ipv4');
    expect(detectType('other', detectors)).toBe('extension');
  });

  it('preserves registry order for equal priorities, including MD5 vs JA3', () => {
    const detectors = compileTypeDetectors({
      md5: { regex: '^[a-fA-F0-9]{32}$', case_sensitive: true },
      ja3: { regex: '^[a-fA-F0-9]{32}$', case_sensitive: true, priority: 0 },
      zebra: { regex: '^match$', case_sensitive: true, priority: 5 },
      alpha: { regex: '^match$', case_sensitive: true, priority: 5 }
    });
    expect(detectType('A'.repeat(32), detectors)).toBe('md5');
    expect(detectType('match', detectors)).toBe('zebra');
  });

  it('skips null regexes, defaults priorities to zero and supports negative priorities', () => {
    const detectors = compileTypeDetectors({
      explicit: { regex: null, case_sensitive: true, priority: 100 },
      fallback: { regex: '^.+$', case_sensitive: true, priority: -1 },
      specific: { regex: '^match$', case_sensitive: true }
    });
    expect(detectors.map(([type]) => type)).toEqual(['specific', 'fallback']);
    expect(detectType('match', detectors)).toBe('specific');
    expect(detectType('other', detectors)).toBe('fallback');
    expect(detectType('', detectors)).toBeNull();
  });
});
