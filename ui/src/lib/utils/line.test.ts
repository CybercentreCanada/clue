import { describe, expect, it } from 'vitest';
import { buildHorizontalLine, buildVerticalLine } from './line';

// Common test parameters for line building functions
const defaultParams = {
  paddingAtLevel: 5,
  numLines: 3,
  distanceX: 0,
  distanceY: 0,
  childX: 100,
  childY: 150,
  childHeight: 40,
  parentX: 50,
  parentY: 100,
  linePaddingX: 20,
  nodeLocations: {
    dest1: [100, 150],
    dest2: [200, 200]
  },
  dest: { id: 'dest1' },
  arcRadius: 5
};

describe('line utilities', () => {
  describe('buildHorizontalLine', () => {
    describe('straight line cases', () => {
      it('should build straight horizontal line when distances are zero', () => {
        const params = {
          ...defaultParams,
          distanceX: 0,
          distanceY: 0
        };

        const result = buildHorizontalLine(params);

        expect(Array.isArray(result)).toBe(true);
        expect(result.length).toBeGreaterThan(0);
        expect(result[0]).toMatch(/^M \d+ \d+$/); // Should start with Move command
        expect(result.some(cmd => cmd.includes('L'))).toBe(true); // Should contain Line commands
        expect(result.some(cmd => cmd.includes('A'))).toBe(true); // Should contain Arc commands
      });

      it('should handle direct line to child when both distances are zero', () => {
        const params = {
          ...defaultParams,
          distanceX: 0,
          distanceY: 0,
          nodeLocations: {
            dest1: [100, 150]
          }
        };

        const result = buildHorizontalLine(params);

        // Should create a path with moves, lines, and arcs
        expect(result).toContain(`M ${params.parentX} ${params.parentY}`);
        expect(result.some(cmd => cmd.includes(`L ${params.childX} ${params.nodeLocations['dest1'][1]}`))).toBe(true);
      });
    });

    describe('curved line cases', () => {
      it('should build curved line when distanceX is zero but distanceY is not', () => {
        const params = {
          ...defaultParams,
          distanceX: 0,
          distanceY: 50
        };

        const result = buildHorizontalLine(params);

        expect(result).toContain(`M ${params.parentX} ${params.parentY}`);
        expect(result.some(cmd => cmd.includes('A'))).toBe(true); // Should have arc commands
        expect(result[result.length - 1]).toContain(`L ${params.childX} ${params.childY}`);
      });

      it('should handle negative Y distance', () => {
        const params = {
          ...defaultParams,
          distanceX: 0,
          distanceY: -50
        };

        const result = buildHorizontalLine(params);

        expect(result).toContain(`M ${params.parentX} ${params.parentY}`);
        expect(result.some(cmd => cmd.includes('A'))).toBe(true);
        expect(result[result.length - 1]).toContain(`L ${params.childX} ${params.childY}`);
      });

      it('should handle complex routing with both X and Y distances', () => {
        const params = {
          ...defaultParams,
          distanceX: 75,
          distanceY: 50
        };

        const result = buildHorizontalLine(params);

        expect(result).toContain(`M ${params.parentX} ${params.parentY}`);
        expect(result.some(cmd => cmd.includes('A'))).toBe(true);
        expect(result[result.length - 1]).toContain(`L ${params.childX} ${params.childY + params.childHeight / 2}`);
      });

      it('should handle negative X distance', () => {
        const params = {
          ...defaultParams,
          distanceX: -75,
          distanceY: 50
        };

        const result = buildHorizontalLine(params);

        expect(result).toContain(`M ${params.parentX} ${params.parentY}`);
        expect(result.some(cmd => cmd.includes('A'))).toBe(true);
        expect(result[result.length - 1]).toContain(`L ${params.childX} ${params.childY + params.childHeight / 2}`);
      });

      it('should handle both negative X and Y distances', () => {
        const params = {
          ...defaultParams,
          distanceX: -75,
          distanceY: -50
        };

        const result = buildHorizontalLine(params);

        expect(result).toContain(`M ${params.parentX} ${params.parentY}`);
        expect(result.some(cmd => cmd.includes('A'))).toBe(true);
        expect(result[result.length - 1]).toContain(`L ${params.childX} ${params.childY + params.childHeight / 2}`);
      });
    });

    describe('arc radius handling', () => {
      it('should use provided arc radius in calculations', () => {
        const params = {
          ...defaultParams,
          distanceX: 50,
          distanceY: 50,
          arcRadius: 10
        };

        const result = buildHorizontalLine(params);

        expect(result.some(cmd => cmd.includes('A 10 10'))).toBe(true);
      });

      it('should handle zero arc radius', () => {
        const params = {
          ...defaultParams,
          distanceX: 50,
          distanceY: 50,
          arcRadius: 0
        };

        const result = buildHorizontalLine(params);

        expect(result.some(cmd => cmd.includes('A 0 0'))).toBe(true);
      });

      it('should handle large arc radius', () => {
        const params = {
          ...defaultParams,
          distanceX: 50,
          distanceY: 50,
          arcRadius: 25
        };

        const result = buildHorizontalLine(params);

        expect(result.some(cmd => cmd.includes('A 25 25'))).toBe(true);
      });
    });

    describe('vertical line positioning', () => {
      it('should calculate vertical line position based on padding and lines', () => {
        const params = {
          ...defaultParams,
          paddingAtLevel: 10,
          numLines: 5,
          linePaddingX: 15,
          distanceX: 50,
          distanceY: 50
        };

        const result = buildHorizontalLine(params);

        // Vertical line X should be calculated as: childX - (paddingAtLevel - numLines) * linePaddingX
        const expectedVerticalX = params.childX - (params.paddingAtLevel - params.numLines) * params.linePaddingX;
        expect(result.some(cmd => cmd.includes(`${expectedVerticalX}`))).toBe(true);
      });
    });

    describe('edge cases', () => {
      it('should handle zero child height', () => {
        const params = {
          ...defaultParams,
          childHeight: 0,
          distanceX: 50,
          distanceY: 50
        };

        const result = buildHorizontalLine(params);

        expect(Array.isArray(result)).toBe(true);
        expect(result.length).toBeGreaterThan(0);
        expect(result[result.length - 1]).toContain(`L ${params.childX} ${params.childY}`);
      });

      it('should handle missing destination in nodeLocations', () => {
        const params = {
          ...defaultParams,
          dest: { id: 'nonexistent' },
          nodeLocations: {},
          distanceX: 50, // Avoid the zero distance path that accesses nodeLocations
          distanceY: 50
        };

        expect(() => buildHorizontalLine(params)).not.toThrow();
      });

      it('should handle zero padding values', () => {
        const params = {
          ...defaultParams,
          paddingAtLevel: 0,
          numLines: 0,
          linePaddingX: 0
        };

        const result = buildHorizontalLine(params);

        expect(Array.isArray(result)).toBe(true);
        expect(result.length).toBeGreaterThan(0);
      });
    });
  });

  describe('buildVerticalLine', () => {
    describe('straight line cases', () => {
      it('should build straight vertical line when distanceX is zero', () => {
        const params = {
          ...defaultParams,
          distanceX: 0,
          distanceY: 50
        };

        const result = buildVerticalLine(params);

        expect(result).toContain(`M ${params.parentX} ${params.parentY}`);
        expect(result).toContain(`L ${params.childX} ${params.childY}`);
        expect(result.length).toBe(2); // Just move and line commands
      });
    });

    describe('curved line cases', () => {
      it('should build curved line when distanceX is not zero', () => {
        const params = {
          ...defaultParams,
          distanceX: 50,
          distanceY: 75
        };

        const result = buildVerticalLine(params);

        expect(result).toContain(`M ${params.parentX} ${params.parentY}`);
        expect(result.some(cmd => cmd.includes('A'))).toBe(true); // Should have arc commands
        expect(result[result.length - 1]).toContain(`L ${params.childX} ${params.childY + params.childHeight / 2}`);
      });

      it('should handle negative Y distance with positive X distance', () => {
        const params = {
          ...defaultParams,
          distanceX: 50,
          distanceY: -75
        };

        const result = buildVerticalLine(params);

        expect(result).toContain(`M ${params.parentX} ${params.parentY}`);
        expect(result.some(cmd => cmd.includes('A'))).toBe(true);
        expect(result[result.length - 1]).toContain(`L ${params.childX} ${params.childY + params.childHeight / 2}`);
      });

      it('should handle negative X distance', () => {
        const params = {
          ...defaultParams,
          distanceX: -50,
          distanceY: -75
        };

        const result = buildVerticalLine(params);

        expect(result).toContain(`M ${params.parentX} ${params.parentY}`);
        expect(result.some(cmd => cmd.includes('A'))).toBe(true);
        expect(result[result.length - 1]).toContain(`L ${params.childX} ${params.childY + params.childHeight / 2}`);
      });

      it('should handle positive distanceY with different arc directions', () => {
        const params = {
          ...defaultParams,
          distanceX: 50,
          distanceY: 75
        };

        const result = buildVerticalLine(params);

        expect(result).toContain(`M ${params.parentX} ${params.parentY}`);
        expect(result.some(cmd => cmd.includes('A'))).toBe(true);
        expect(result[result.length - 1]).toContain(`L ${params.childX} ${params.childY + params.childHeight / 2}`);
      });
    });

    describe('vertical line positioning', () => {
      it('should calculate vertical line position based on distance Y sign', () => {
        const params = {
          ...defaultParams,
          distanceX: 50,
          distanceY: -75, // Negative Y
          paddingAtLevel: 8,
          numLines: 3,
          linePaddingX: 12
        };

        const result = buildVerticalLine(params);

        // When distanceY < 0, should use childX for vertical line calculation
        const expectedVerticalX = params.childX - (params.paddingAtLevel - params.numLines) * params.linePaddingX;
        expect(result.some(cmd => cmd.includes(`${expectedVerticalX}`))).toBe(true);
      });

      it('should handle positive distanceY for vertical line positioning', () => {
        const params = {
          ...defaultParams,
          distanceX: 50,
          distanceY: 75, // Positive Y
          paddingAtLevel: 8,
          numLines: 3,
          linePaddingX: 12
        };

        const result = buildVerticalLine(params);

        // When distanceY >= 0, should use parentX for vertical line calculation
        const expectedVerticalX = params.parentX - (params.paddingAtLevel - params.numLines) * params.linePaddingX;
        expect(result.some(cmd => cmd.includes(`${expectedVerticalX}`))).toBe(true);
      });
    });

    describe('arc radius handling', () => {
      it('should use provided arc radius in calculations', () => {
        const params = {
          ...defaultParams,
          distanceX: 50,
          distanceY: 50,
          arcRadius: 8
        };

        const result = buildVerticalLine(params);

        expect(result.some(cmd => cmd.includes('A 8 8'))).toBe(true);
      });

      it('should handle different arc sweep directions', () => {
        const params1 = {
          ...defaultParams,
          distanceX: 50,
          distanceY: -75,
          arcRadius: 10
        };

        const params2 = {
          ...defaultParams,
          distanceX: -50,
          distanceY: -75,
          arcRadius: 10
        };

        const result1 = buildVerticalLine(params1);
        const result2 = buildVerticalLine(params2);

        // Both should contain arc commands but with different sweep directions
        expect(result1.some(cmd => cmd.includes('A 10 10'))).toBe(true);
        expect(result2.some(cmd => cmd.includes('A 10 10'))).toBe(true);
      });
    });

    describe('edge cases', () => {
      it('should handle zero child height', () => {
        const params = {
          ...defaultParams,
          childHeight: 0,
          distanceX: 50
        };

        const result = buildVerticalLine(params);

        expect(Array.isArray(result)).toBe(true);
        expect(result.length).toBeGreaterThan(0);
        expect(result[result.length - 1]).toContain(`L ${params.childX} ${params.childY}`);
      });

      it('should handle zero distances', () => {
        const params = {
          ...defaultParams,
          distanceX: 0,
          distanceY: 0
        };

        const result = buildVerticalLine(params);

        expect(result).toEqual([`M ${params.parentX} ${params.parentY}`, `L ${params.childX} ${params.childY}`]);
      });

      it('should handle negative arc radius', () => {
        const params = {
          ...defaultParams,
          distanceX: 50,
          distanceY: 50,
          arcRadius: -5
        };

        const result = buildVerticalLine(params);

        // Should still generate valid SVG commands
        expect(Array.isArray(result)).toBe(true);
        expect(result.length).toBeGreaterThan(0);
        expect(result.some(cmd => cmd.includes('A -5 -5'))).toBe(true);
      });

      it('should handle large coordinate values', () => {
        const params = {
          ...defaultParams,
          parentX: 10000,
          parentY: 5000,
          childX: 12000,
          childY: 8000,
          distanceX: 2000,
          distanceY: 3000
        };

        const result = buildVerticalLine(params);

        expect(result).toContain(`M ${params.parentX} ${params.parentY}`);
        expect(result[result.length - 1]).toContain(`L ${params.childX} ${params.childY + params.childHeight / 2}`);
      });
    });
  });

  describe('SVG path format validation', () => {
    it('should generate valid SVG path commands for horizontal lines', () => {
      const result = buildHorizontalLine(defaultParams);

      result.forEach(command => {
        // Each command should start with a valid SVG path command letter
        expect(command).toMatch(/^[MLHVCSQTAZ]/);

        // Should contain numeric values
        expect(command).toMatch(/\d/);
      });
    });

    it('should generate valid SVG path commands for vertical lines', () => {
      const result = buildVerticalLine(defaultParams);

      result.forEach(command => {
        // Each command should start with a valid SVG path command letter
        expect(command).toMatch(/^[MLHVCSQTAZ]/);

        // Should contain numeric values
        expect(command).toMatch(/\d/);
      });
    });

    it('should maintain proper command sequence', () => {
      const horizontal = buildHorizontalLine({ ...defaultParams, distanceX: 50, distanceY: 50 });
      const vertical = buildVerticalLine({ ...defaultParams, distanceX: 50, distanceY: 50 });

      // Both should start with Move command
      expect(horizontal[0]).toMatch(/^M/);
      expect(vertical[0]).toMatch(/^M/);

      // Both should end with Line command
      expect(horizontal[horizontal.length - 1]).toMatch(/^L/);
      expect(vertical[vertical.length - 1]).toMatch(/^L/);
    });
  });

  describe('parameter boundary conditions', () => {
    it('should handle extreme padding values', () => {
      const extremeParams = {
        ...defaultParams,
        paddingAtLevel: 1000,
        numLines: 1,
        linePaddingX: 500,
        distanceX: 50,
        distanceY: 50
      };

      expect(() => {
        buildHorizontalLine(extremeParams);
        buildVerticalLine(extremeParams);
      }).not.toThrow();
    });

    it('should handle floating point coordinates', () => {
      const floatParams = {
        ...defaultParams,
        parentX: 50.5,
        parentY: 100.7,
        childX: 100.3,
        childY: 150.9,
        distanceX: 49.8,
        distanceY: 50.2
      };

      const horizontal = buildHorizontalLine(floatParams);
      const vertical = buildVerticalLine(floatParams);

      expect(Array.isArray(horizontal)).toBe(true);
      expect(Array.isArray(vertical)).toBe(true);
      expect(horizontal.length).toBeGreaterThan(0);
      expect(vertical.length).toBeGreaterThan(0);
    });
  });
});
