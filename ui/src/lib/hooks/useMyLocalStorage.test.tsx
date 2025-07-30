import { act, renderHook } from '@testing-library/react';
import LocalStorageProvider from 'components/app/providers/LocalStorageProvider';
import { MY_LOCAL_STORAGE_PREFIX, StorageKey } from 'lib/utils/constants';
import { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import MockLocalStorage from '../../tests/MockLocalStorage';
import useMyLocalStorage, { useMyLocalStorageItem, useMyLocalStorageProvider } from './useMyLocalStorage';

const localStorageMock: any = new MockLocalStorage();

// Replace global localStorage with mock
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true
});

// Test wrapper component with LocalStorageProvider
const TestWrapper = ({ children }: { children: ReactNode }) => <LocalStorageProvider>{children}</LocalStorageProvider>;

describe('useMyLocalStorage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
  });

  describe('useMyLocalStorage', () => {
    it('should return localStorage utilities with correct prefix', () => {
      const { result } = renderHook(() => useMyLocalStorage());

      expect(result.current).toHaveProperty('get');
      expect(result.current).toHaveProperty('set');
      expect(result.current).toHaveProperty('remove');
      expect(result.current).toHaveProperty('has');
      expect(result.current).toHaveProperty('keys');
      expect(result.current).toHaveProperty('items');
      expect(result.current).toHaveProperty('clear');
    });

    it('should set and get values with prefix', () => {
      const { result } = renderHook(() => useMyLocalStorage());
      const testKey = 'test-key';
      const testValue = { data: 'test-value' };

      act(() => {
        result.current.set(testKey, testValue);
      });

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.${testKey}`,
        JSON.stringify(testValue)
      );

      const retrieved = result.current.get(testKey);
      expect(retrieved).toEqual(testValue);
    });

    it('should check if key exists', () => {
      const { result } = renderHook(() => useMyLocalStorage());
      const testKey = 'exists-key';

      expect(result.current.has(testKey)).toBe(false);

      act(() => {
        result.current.set(testKey, 'value');
      });

      expect(result.current.has(testKey)).toBe(true);
    });

    it('should remove items with and without prefix', () => {
      const { result } = renderHook(() => useMyLocalStorage());
      const testKey = 'remove-key';

      act(() => {
        result.current.set(testKey, 'value');
      });

      expect(result.current.has(testKey)).toBe(true);

      act(() => {
        result.current.remove(testKey);
      });

      expect(result.current.has(testKey)).toBe(false);
      expect(localStorageMock.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.${testKey}`);

      // Test removing with prefix flag
      const fullKey = `${MY_LOCAL_STORAGE_PREFIX}.direct-key`;
      localStorageMock.setItem(fullKey, JSON.stringify('direct-value'));

      act(() => {
        result.current.remove(fullKey, true);
      });

      expect(localStorageMock.removeItem).toHaveBeenCalledWith(fullKey);
    });

    it('should get all keys', () => {
      const { result } = renderHook(() => useMyLocalStorage());

      act(() => {
        result.current.set('key1', 'value1');
        result.current.set('key2', 'value2');
      });

      const keys = result.current.keys();
      expect(keys).toContain(`${MY_LOCAL_STORAGE_PREFIX}.key1`);
      expect(keys).toContain(`${MY_LOCAL_STORAGE_PREFIX}.key2`);
    });

    it('should get all items', () => {
      const { result } = renderHook(() => useMyLocalStorage());

      act(() => {
        result.current.set('item1', 'value1');
        result.current.set('item2', { data: 'value2' });
      });

      expect(Object.keys(localStorageMock)).toEqual(['clue.ui.item1', 'clue.ui.item2']);

      const items = result.current.items();
      expect(items).toEqual([
        { key: `${MY_LOCAL_STORAGE_PREFIX}.item1`, value: 'value1' },
        { key: `${MY_LOCAL_STORAGE_PREFIX}.item2`, value: { data: 'value2' } }
      ]);
    });

    it('should clear all prefixed items', () => {
      const { result } = renderHook(() => useMyLocalStorage());

      // Add some prefixed items
      act(() => {
        result.current.set('clear1', 'value1');
        result.current.set('clear2', 'value2');
      });

      // Add non-prefixed item directly
      localStorageMock.setItem('other-key', JSON.stringify('other-value'));

      act(() => {
        result.current.clear();
      });

      // Prefixed items should be removed
      expect(result.current.has('clear1')).toBe(false);
      expect(result.current.has('clear2')).toBe(false);

      // Non-prefixed item should remain
      expect(localStorageMock.getItem('other-key')).toBe(JSON.stringify('other-value'));
    });

    it('should handle JSON parsing errors gracefully', () => {
      const { result } = renderHook(() => useMyLocalStorage());

      // Set invalid JSON directly
      localStorageMock.setItem(`${MY_LOCAL_STORAGE_PREFIX}.invalid`, 'invalid-json{');

      expect(() => {
        result.current.get('invalid');
      }).toThrow();
    });
  });

  describe('useMyLocalStorageItem', () => {
    it('should initialize with initial value when key does not exist', () => {
      const initialValue = 'initial-value';
      const { result } = renderHook(() => useMyLocalStorageItem(StorageKey.PROVIDER, initialValue));

      const [value] = result.current;
      expect(value).toBe(initialValue);

      // Should have saved initial value to localStorage
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.${StorageKey.PROVIDER}`,
        JSON.stringify(initialValue)
      );
    });

    it('should initialize with stored value when key exists', () => {
      const storedValue = 'stored-value';
      localStorageMock.setItem(`${MY_LOCAL_STORAGE_PREFIX}.${StorageKey.PROVIDER}`, JSON.stringify(storedValue));

      const { result } = renderHook(() => useMyLocalStorageItem(StorageKey.PROVIDER, 'initial-value'));

      const [value] = result.current;
      expect(value).toBe(storedValue);
    });

    it('should update value and save to localStorage', () => {
      const { result } = renderHook(() => useMyLocalStorageItem(StorageKey.PROVIDER, 'initial'));

      const [, setValue] = result.current;
      const newValue = 'new-value';

      act(() => {
        setValue(newValue);
      });

      const [updatedValue] = result.current;
      expect(updatedValue).toBe(newValue);
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.${StorageKey.PROVIDER}`,
        JSON.stringify(newValue)
      );
    });

    it('should update value without saving when save=false', () => {
      const { result } = renderHook(() => useMyLocalStorageItem(StorageKey.PROVIDER, 'initial'));

      const [, setValue] = result.current;
      const newValue = 'new-value';

      // Clear previous calls
      vi.clearAllMocks();

      act(() => {
        setValue(newValue, false);
      });

      const [updatedValue] = result.current;
      expect(updatedValue).toBe(newValue);
      // Should not have called setItem for the new value
      expect(localStorageMock.setItem).not.toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.${StorageKey.PROVIDER}`,
        JSON.stringify(newValue)
      );
    });

    it('should remove item from localStorage when setting null or undefined', () => {
      const { result } = renderHook(() => useMyLocalStorageItem(StorageKey.PROVIDER, 'initial'));

      const [, setValue] = result.current;

      act(() => {
        setValue(null);
      });

      expect(localStorageMock.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.${StorageKey.PROVIDER}`);

      act(() => {
        setValue(undefined);
      });

      expect(localStorageMock.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.${StorageKey.PROVIDER}`);
    });

    it('should remove item using remove function', () => {
      const { result } = renderHook(() => useMyLocalStorageItem(StorageKey.PROVIDER, 'initial'));

      const [, , removeValue] = result.current;

      act(() => {
        removeValue();
      });

      expect(localStorageMock.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.${StorageKey.PROVIDER}`);
    });

    it('should work with complex objects', () => {
      const complexObject = {
        user: { id: 1, name: 'John' },
        settings: { theme: 'dark', notifications: true },
        array: [1, 2, 3]
      };

      const { result } = renderHook(() => useMyLocalStorageItem(StorageKey.PROVIDER, complexObject));

      const [value, setValue] = result.current;
      expect(value).toEqual(complexObject);

      const updatedObject = { ...complexObject, user: { ...complexObject.user, name: 'Jane' } };

      act(() => {
        setValue(updatedObject);
      });

      const [updatedValue] = result.current;
      expect(updatedValue).toEqual(updatedObject);
    });

    it('should not set initial value when initial value is null or undefined', () => {
      vi.clearAllMocks();

      renderHook(() => useMyLocalStorageItem(StorageKey.PROVIDER, null));

      expect(localStorageMock.setItem).not.toHaveBeenCalled();

      renderHook(() => useMyLocalStorageItem(StorageKey.PROVIDER, undefined));

      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });
  });

  describe('useMyLocalStorageProvider', () => {
    it('should return context value when used within provider', () => {
      const { result } = renderHook(() => useMyLocalStorageProvider(), {
        wrapper: TestWrapper
      });

      expect(result.current).toBeDefined();
      expect(result.current).toHaveProperty('values');
      expect(result.current).toHaveProperty('set');
      expect(result.current).toHaveProperty('remove');
    });

    it('should return null when used outside provider', () => {
      const { result } = renderHook(() => useMyLocalStorageProvider());

      expect(result.current).toBeNull();
    });

    it('should update values through context', () => {
      const { result } = renderHook(() => useMyLocalStorageProvider(), {
        wrapper: TestWrapper
      });

      const testValue = 'context-value';

      act(() => {
        result.current?.set(StorageKey.PROVIDER, testValue);
      });

      expect(result.current?.values[StorageKey.PROVIDER]).toBe(testValue);
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        `${MY_LOCAL_STORAGE_PREFIX}.${StorageKey.PROVIDER}`,
        JSON.stringify(testValue)
      );
    });

    it('should remove values through context', () => {
      const { result } = renderHook(() => useMyLocalStorageProvider(), {
        wrapper: TestWrapper
      });

      // First set a value
      act(() => {
        result.current?.set(StorageKey.PROVIDER, 'test-value');
      });

      expect(result.current?.values[StorageKey.PROVIDER]).toBe('test-value');

      // Then remove it
      act(() => {
        result.current?.remove(StorageKey.PROVIDER);
      });

      expect(result.current?.values[StorageKey.PROVIDER]).toBeUndefined();
      expect(localStorageMock.removeItem).toHaveBeenCalledWith(`${MY_LOCAL_STORAGE_PREFIX}.${StorageKey.PROVIDER}`);
    });

    it('should initialize with existing localStorage values', () => {
      // Pre-populate localStorage
      const existingValue = 'existing-value';
      localStorageMock.setItem(`${MY_LOCAL_STORAGE_PREFIX}.${StorageKey.COLOR_SCHEME}`, JSON.stringify(existingValue));

      const { result } = renderHook(() => useMyLocalStorageProvider(), {
        wrapper: TestWrapper
      });

      // Allow the effect to run
      expect(result.current?.values[StorageKey.COLOR_SCHEME]).toBe(existingValue);
    });
  });
});
