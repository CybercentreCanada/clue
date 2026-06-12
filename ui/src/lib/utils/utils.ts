import { flatten, unflatten } from 'flat';
import type { FailedRequest } from 'lib/types/lookup';
import { dayjs } from 'lib/utils/time';
import isArray from 'lodash-es/isArray';
import isEmpty from 'lodash-es/isEmpty';
import isEqual from 'lodash-es/isEqual';
import isNil from 'lodash-es/isNil';
import isPlainObject from 'lodash-es/isPlainObject';
import uniqWith from 'lodash-es/uniqWith';

export const twitterShort = (date: string | Date | number): string => {
  if (!date || date === '?') {
    return '?';
  }

  const now = dayjs();
  const comparedDate = dayjs(date);

  if (comparedDate.isAfter(now)) {
    return now.fromNow();
  }

  return comparedDate.fromNow();
};

// Adapted from here: https://stackoverflow.com/a/48429492
export const delay = (ms: number, rejectOnCancel = false) => {
  let timerId: number | NodeJS.Timeout;
  let onCancel: () => void;

  class TimedPromise extends Promise<void> {
    cancel = () => {
      if (rejectOnCancel) {
        onCancel();
      }

      clearTimeout(timerId);
    };
  }

  return new TimedPromise((resolve, reject) => {
    timerId = setTimeout(resolve, ms);
    onCancel = reject;
  });
};

export const removeEmpty = (obj: any, aggressive = false) => {
  if (aggressive && isEmpty(obj)) {
    return null;
  } else if (isArray(obj)) {
    return obj;
  }

  return Object.fromEntries(
    Object.entries(obj ?? {})
      .filter(([__, v]) => !isNil(v))
      .map(([k, v]) => [k, isPlainObject(v) || isArray(v) ? removeEmpty(v, aggressive) : v])
      .filter(([__, v]) => !!v)
  );
};

export const searchObject = (o: any, query: string) => {
  try {
    const regex = new RegExp(query, 'i');

    return unflatten(
      Object.fromEntries(Object.entries(flatten(o)).filter(([k, v]) => regex.test(k) || regex.test(v))) ?? {}
    );
  } catch {
    return o;
  }
};

export const filterEnrichments = (failedEnrichments: FailedRequest[]) => {
  return uniqWith<FailedRequest>(failedEnrichments, isEqual);
};

/**
 * Deterministically compute a status ID from query fields.
 * Uses WebCrypto SHA-256 when available, falls back to a lightweight FNV-1a.
 */
export const computeStatusId = async (type: string, value: string, classification: string): Promise<string> => {
  const input = `${type}::${value}::${classification}`.toLowerCase();

  try {
    // Prefer WebCrypto for a stable, collision-resistant hash
    const encoder = new TextEncoder();
    const data = encoder.encode(input);
    const digest = await (globalThis.crypto?.subtle?.digest?.('SHA-256', data) ?? Promise.reject());
    const bytes = new Uint8Array(digest as ArrayBuffer);
    let hex = '';
    for (let i = 0; i < bytes.length; i++) {
      hex += bytes[i].toString(16).padStart(2, '0');
    }
    return hex;
  } catch {
    // Fallback: FNV-1a 32-bit hash
    let hash = 0x811c9dc5;
    for (let i = 0; i < input.length; i++) {
      hash ^= input.charCodeAt(i);
      hash += (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24);
    }
    return (hash >>> 0).toString(16);
  }
};
