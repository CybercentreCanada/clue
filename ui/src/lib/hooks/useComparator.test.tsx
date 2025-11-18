import { createTheme, ThemeProvider } from '@mui/material/styles';
import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BaseComparator, EdgeStyler, NodeStyler, Operator } from '../types/graph';
import useComparator from './useComparator';

// Mock tinycolor2
vi.mock('tinycolor2', () => ({
  default: vi.fn((color: string) => ({
    darken: vi.fn(() => ({
      toString: vi.fn(() => {
        if (color === 'invalid-color') {
          throw new Error('Invalid color');
        }

        return `${color}-darkened`;
      })
    }))
  }))
}));

// Create a test theme
const testTheme = createTheme({
  palette: {
    primary: {
      main: '#1976d2'
    },
    secondary: {
      main: '#dc004e'
    },
    error: {
      main: '#f44336'
    },
    warning: {
      main: '#ff9800'
    },
    info: {
      main: '#2196f3'
    },
    success: {
      main: '#4caf50'
    }
  }
});

// Test wrapper with theme provider
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <ThemeProvider theme={testTheme}>{children}</ThemeProvider>
);

describe('useComparator', () => {
  let comparator: ReturnType<typeof useComparator>;

  beforeEach(() => {
    vi.clearAllMocks();
    const { result } = renderHook(() => useComparator(), {
      wrapper: TestWrapper
    });
    comparator = result.current;
  });

  describe('runOperator functionality', () => {
    const testNode = { name: 'test', age: 25, score: 85.5, active: true };

    describe('equality operator (=)', () => {
      it('should handle string equality', () => {
        const baseComp: BaseComparator = { field: 'name', operator: '=', value: 'test' };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(true);
      });

      it('should handle number equality', () => {
        const baseComp: BaseComparator = { field: 'age', operator: '=', value: 25 };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(true);
      });

      it('should handle inequality', () => {
        const baseComp: BaseComparator = { field: 'name', operator: '=', value: 'different' };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(false);
      });

      it('should handle null/undefined values', () => {
        const nullNode = { name: null };
        const baseComp: BaseComparator = { field: 'name', operator: '=', value: '' };
        const result = comparator.runComparator(baseComp, nullNode);
        expect(result).toBe(true);
      });
    });

    describe('inequality operator (!=)', () => {
      it('should return true for different values', () => {
        const baseComp: BaseComparator = { field: 'name', operator: '!=', value: 'different' };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(true);
      });

      it('should return false for same values', () => {
        const baseComp: BaseComparator = { field: 'name', operator: '!=', value: 'test' };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(false);
      });
    });

    describe('less than operator (<)', () => {
      it('should return true when value1 < value2', () => {
        const baseComp: BaseComparator = { field: 'age', operator: '<', value: 30 };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(true);
      });

      it('should return false when value1 >= value2', () => {
        const baseComp: BaseComparator = { field: 'age', operator: '<', value: 20 };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(false);
      });

      it('should handle decimal values', () => {
        const baseComp: BaseComparator = { field: 'score', operator: '<', value: 90.0 };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(true);
      });
    });

    describe('greater than operator (>)', () => {
      it('should return true when value1 > value2', () => {
        const baseComp: BaseComparator = { field: 'age', operator: '>', value: 20 };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(true);
      });

      it('should return false when value1 <= value2', () => {
        const baseComp: BaseComparator = { field: 'age', operator: '>', value: 30 };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(false);
      });
    });

    describe('less than or equal operator (<=)', () => {
      it('should return true when value1 <= value2', () => {
        const baseComp: BaseComparator = { field: 'age', operator: '<=', value: 25 };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(true);
      });

      it('should return false when value1 > value2', () => {
        const baseComp: BaseComparator = { field: 'age', operator: '<=', value: 20 };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(false);
      });
    });

    describe('greater than or equal operator (>=)', () => {
      it('should return true when value1 >= value2', () => {
        const baseComp: BaseComparator = { field: 'age', operator: '>=', value: 25 };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(true);
      });

      it('should return false when value1 < value2', () => {
        const baseComp: BaseComparator = { field: 'age', operator: '>=', value: 30 };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(false);
      });
    });

    describe('contains operator (~)', () => {
      it('should return true when value1 contains value2', () => {
        const baseComp: BaseComparator = { field: 'name', operator: '~', value: 'es' };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(true);
      });

      it('should be case insensitive', () => {
        const baseComp: BaseComparator = { field: 'name', operator: '~', value: 'TES' };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(true);
      });

      it('should return false when value1 does not contain value2', () => {
        const baseComp: BaseComparator = { field: 'name', operator: '~', value: 'xyz' };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(false);
      });

      it('should handle null/undefined values', () => {
        const nullNode = { name: null };
        const baseComp: BaseComparator = { field: 'name', operator: '~', value: 'test' };
        const result = comparator.runComparator(baseComp, nullNode);
        expect(result).toBe(false);
      });
    });

    describe('edge cases', () => {
      it('should return true when operator is missing', () => {
        const baseComp = { field: 'name', operator: undefined as any, value: 'test' };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(true);
      });

      it('should return true when value2 is missing', () => {
        const baseComp = { field: 'name', operator: '=' as Operator, value: undefined as any };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(true);
      });

      it('should return false for unknown operators', () => {
        const baseComp = { field: 'name', operator: 'unknown' as Operator, value: 'test' };
        const result = comparator.runComparator(baseComp, testNode);
        expect(result).toBe(false);
      });
    });
  });

  describe('NodeStyler functionality', () => {
    const testNode = { name: 'test', priority: 5 };

    it('should return styles when condition is met', () => {
      const nodeStyler: NodeStyler = {
        type: 'node',
        field: 'name',
        operator: '=',
        value: 'test',
        color: 'primary',
        size: 2
      };

      const result = comparator.runComparator(nodeStyler, testNode);
      expect(result).toEqual({
        fill: '#1976d2',
        stroke: '#1976d2-darkened',
        strokeWidth: 2,
        fontSize: 2
      });
    });

    it('should return empty styles when condition is not met', () => {
      const nodeStyler: NodeStyler = {
        type: 'node',
        field: 'name',
        operator: '=',
        value: 'different',
        color: 'primary',
        size: 2
      };

      const result = comparator.runComparator(nodeStyler, testNode);
      expect(result).toEqual({});
    });

    it('should handle custom color values', () => {
      const nodeStyler: NodeStyler = {
        type: 'node',
        field: 'name',
        operator: '=',
        value: 'test',
        color: '#ff0000'
      };

      const result = comparator.runComparator(nodeStyler, testNode);
      expect(result).toEqual({
        fill: '#ff0000',
        stroke: '#ff0000-darkened'
      });
    });

    it('should handle tinycolor error gracefully', async () => {
      const nodeStyler: NodeStyler = {
        type: 'node',
        field: 'name',
        operator: '=',
        value: 'test',
        color: 'invalid-color'
      };

      const result = comparator.runComparator(nodeStyler, testNode);
      expect(result).toEqual({
        fill: 'invalid-color',
        stroke: 'invalid-color'
      });
    });

    it('should handle only color styling', () => {
      const nodeStyler: NodeStyler = {
        type: 'node',
        field: 'name',
        operator: '=',
        value: 'test',
        color: 'error'
      };

      const result = comparator.runComparator(nodeStyler, testNode);
      expect(result).toEqual({
        fill: '#f44336',
        stroke: '#f44336-darkened'
      });
    });

    it('should handle only size styling', () => {
      const nodeStyler: NodeStyler = {
        type: 'node',
        field: 'name',
        operator: '=',
        value: 'test',
        size: 3
      };

      const result = comparator.runComparator(nodeStyler, testNode);
      expect(result).toEqual({
        strokeWidth: 3,
        fontSize: 3
      });
    });

    it('should handle nested field access', () => {
      const nestedNode = { user: { profile: { name: 'john' } } };
      const nodeStyler: NodeStyler = {
        type: 'node',
        field: 'user.profile.name',
        operator: '=',
        value: 'john',
        color: 'success'
      };

      const result = comparator.runComparator(nodeStyler, nestedNode);
      expect(result).toEqual({
        fill: '#4caf50',
        stroke: '#4caf50-darkened'
      });
    });
  });

  describe('EdgeStyler functionality', () => {
    const sourceNode = { id: '1', name: 'source' };
    const targetNode = { id: '2', name: 'target' };

    it('should return empty styles for edge stylers (not implemented)', () => {
      const edgeStyler: EdgeStyler = {
        type: 'edge',
        source: { field: 'name', operator: '=', value: 'source' },
        operator: '=',
        target: { field: 'name', operator: '=', value: 'target' }
      };

      const result = comparator.runComparator(edgeStyler, sourceNode, targetNode);
      expect(result).toEqual({});
    });
  });

  describe('runComparators functionality', () => {
    const testNode = { name: 'test', priority: 5, active: true };

    it('should combine multiple comparators', () => {
      const comparators: NodeStyler[] = [
        {
          type: 'node',
          field: 'name',
          operator: '=',
          value: 'test',
          color: 'primary'
        },
        {
          type: 'node',
          field: 'priority',
          operator: '>',
          value: 3,
          size: 2
        }
      ];

      const result = comparator.runComparators(comparators, testNode);
      expect(result).toEqual({
        fill: '#1976d2',
        stroke: '#1976d2-darkened',
        strokeWidth: 2,
        fontSize: 2
      });
    });

    it('should handle overlapping styles (last one wins)', () => {
      const comparators: NodeStyler[] = [
        {
          type: 'node',
          field: 'name',
          operator: '=',
          value: 'test',
          color: 'primary',
          size: 1
        },
        {
          type: 'node',
          field: 'active',
          operator: '=',
          value: 'true',
          color: 'success',
          size: 3
        }
      ];

      const result = comparator.runComparators(comparators, testNode);
      expect(result).toEqual({
        fill: '#4caf50',
        stroke: '#4caf50-darkened',
        strokeWidth: 3,
        fontSize: 3
      });
    });

    it('should handle empty comparators array', () => {
      const result = comparator.runComparators([], testNode);
      expect(result).toEqual({});
    });

    it('should handle null/undefined comparators', () => {
      const result = comparator.runComparators(null as any, testNode);
      expect(result).toEqual({});
    });

    it('should skip comparators that do not match', () => {
      const comparators: NodeStyler[] = [
        {
          type: 'node',
          field: 'name',
          operator: '=',
          value: 'different',
          color: 'primary'
        },
        {
          type: 'node',
          field: 'priority',
          operator: '>',
          value: 3,
          size: 2
        }
      ];

      const result = comparator.runComparators(comparators, testNode);
      expect(result).toEqual({
        strokeWidth: 2,
        fontSize: 2
      });
    });

    it('should work with mixed node and edge stylers', () => {
      const mixedComparators = [
        {
          type: 'node',
          field: 'name',
          operator: '=',
          value: 'test',
          color: 'primary'
        } as NodeStyler,
        {
          type: 'edge',
          source: { field: 'name', operator: '=', value: 'source' },
          operator: '=',
          target: { field: 'name', operator: '=', value: 'target' }
        } as EdgeStyler
      ];

      const result = comparator.runComparators(mixedComparators, testNode);
      expect(result).toEqual({
        fill: '#1976d2',
        stroke: '#1976d2-darkened'
      });
    });
  });

  describe('type guards', () => {
    it('should correctly identify BaseComparator', () => {
      const baseComp: BaseComparator = { field: 'name', operator: '=', value: 'test' };
      const nodeStyler: NodeStyler = { type: 'node', field: 'name', operator: '=', value: 'test' };

      // Test through the actual functionality
      const baseResult = comparator.runComparator(baseComp, { name: 'test' });
      const nodeResult = comparator.runComparator(nodeStyler, { name: 'test' });

      expect(typeof baseResult).toBe('boolean');
      expect(typeof nodeResult).toBe('object');
    });

    it('should correctly identify NodeStyler vs EdgeStyler', () => {
      const nodeStyler: NodeStyler = { type: 'node', field: 'name', operator: '=', value: 'test' };
      const edgeStyler: EdgeStyler = {
        type: 'edge',
        source: { field: 'name', operator: '=', value: 'source' },
        operator: '=',
        target: { field: 'name', operator: '=', value: 'target' }
      };

      const nodeResult = comparator.runComparator(nodeStyler, { name: 'test' });
      const edgeResult = comparator.runComparator(edgeStyler, { name: 'source' }, { name: 'target' });

      // NodeStyler can return styles, EdgeStyler returns empty object (not implemented)
      expect(nodeResult).toEqual({});
      expect(edgeResult).toEqual({});
    });
  });

  describe('theme integration', () => {
    it('should use theme colors correctly', () => {
      const nodeStyler: NodeStyler = {
        type: 'node',
        field: 'name',
        operator: '=',
        value: 'test',
        color: 'secondary'
      };

      const result = comparator.runComparator(nodeStyler, { name: 'test' });
      expect(result).toEqual({
        fill: '#dc004e',
        stroke: '#dc004e-darkened'
      });
    });

    it('should fallback to color string when not in theme palette', () => {
      const nodeStyler: NodeStyler = {
        type: 'node',
        field: 'name',
        operator: '=',
        value: 'test',
        color: 'nonexistent'
      };

      const result = comparator.runComparator(nodeStyler, { name: 'test' });
      expect(result).toEqual({
        fill: 'nonexistent',
        stroke: 'nonexistent-darkened'
      });
    });
  });
});
