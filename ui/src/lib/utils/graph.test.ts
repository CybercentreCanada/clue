import { NestedDataset, RawEntry } from 'lib/types/graph';
import { describe, expect, it } from 'vitest';
import { createSubGraph, cssImportant, cyrb53, getAllChildren, getPathToRoot, getSubGraphNodeSet } from './graph';

// Test data setup
const createTestNode = (id: string, edges?: string[]): RawEntry => ({
  id,
  edges: edges || [],
  markdown: `Node ${id}`,
  icons: ['test-icon']
});

const testData: RawEntry[][] = [
  // Level 0 - Root level
  [createTestNode('root1'), createTestNode('root2')],
  // Level 1 - Children of root
  [createTestNode('child1', ['root1']), createTestNode('child2', ['root1']), createTestNode('child3', ['root2'])],
  // Level 2 - Grandchildren
  [
    createTestNode('grandchild1', ['child1']),
    createTestNode('grandchild2', ['child1', 'child2']),
    createTestNode('grandchild3', ['child3'])
  ],
  // Level 3 - Great-grandchildren
  [createTestNode('great1', ['grandchild1']), createTestNode('great2', ['grandchild2'])]
];

const testDataset: NestedDataset = {
  id: 'test-dataset',
  metadata: {
    type: 'nested',
    display: {
      visualization: { type: 'tree' }
    }
  },
  data: testData
};

// Complex graph with cycles and multiple edges
const complexData: RawEntry[][] = [
  [createTestNode('A'), createTestNode('B')],
  [createTestNode('C', ['A']), createTestNode('D', ['A', 'B'])],
  [createTestNode('E', ['C', 'D']), createTestNode('F', ['D'])],
  [createTestNode('G', ['E', 'F', 'C'])] // G has multiple parents including a cycle back to C
];

const complexDataset: NestedDataset = {
  id: 'complex-dataset',
  metadata: { type: 'nested' },
  data: complexData
};

describe('graph utilities', () => {
  describe('cyrb53 hash function', () => {
    it('should return consistent hash for same input', () => {
      const input = 'test-string';
      const hash1 = cyrb53(input);
      const hash2 = cyrb53(input);

      expect(hash1).toBe(hash2);
      expect(typeof hash1).toBe('number');
      expect(hash1).toBeGreaterThanOrEqual(0);
      expect(hash1).toBeLessThan(1);
    });

    it('should return different hashes for different inputs', () => {
      const hash1 = cyrb53('string1');
      const hash2 = cyrb53('string2');

      expect(hash1).not.toBe(hash2);
    });

    it('should handle empty string', () => {
      const hash = cyrb53('');
      expect(typeof hash).toBe('number');
      expect(hash).toBeGreaterThanOrEqual(0);
      expect(hash).toBeLessThan(1);
    });

    it('should use seed parameter', () => {
      const input = 'test';
      const hash1 = cyrb53(input, 0);
      const hash2 = cyrb53(input, 1);

      expect(hash1).not.toBe(hash2);
    });

    it('should handle long strings', () => {
      const longString = 'a'.repeat(1000);
      const hash = cyrb53(longString);

      expect(typeof hash).toBe('number');
      expect(hash).toBeGreaterThanOrEqual(0);
      expect(hash).toBeLessThan(1);
    });

    it('should handle unicode characters', () => {
      const unicodeString = '测试字符串🚀';
      const hash = cyrb53(unicodeString);

      expect(typeof hash).toBe('number');
      expect(hash).toBeGreaterThanOrEqual(0);
      expect(hash).toBeLessThan(1);
    });
  });

  describe('cssImportant', () => {
    it('should append !important to CSS property', () => {
      expect(cssImportant('color: red')).toBe('color: red !important');
    });

    it('should handle empty string', () => {
      expect(cssImportant('')).toBe(' !important');
    });

    it('should handle complex CSS properties', () => {
      const property = 'margin: 10px 15px 20px 25px';
      expect(cssImportant(property)).toBe('margin: 10px 15px 20px 25px !important');
    });
  });

  describe('getPathToRoot', () => {
    it('should find path to root for leaf node', () => {
      const path = getPathToRoot('great1', testData);

      expect(path).toBeInstanceOf(Set);
      expect(path.has('great1')).toBe(true);
      expect(path.has('grandchild1')).toBe(true);
      expect(path.has('child1')).toBe(true);
      expect(path.has('root1')).toBe(true);
      expect(path.size).toBe(4);
    });

    it('should find path for node with multiple parents', () => {
      const path = getPathToRoot('grandchild2', testData);

      expect(path.has('grandchild2')).toBe(true);
      expect(path.has('child1')).toBe(true);
      expect(path.has('child2')).toBe(true);
      expect(path.has('root1')).toBe(true);
      expect(path.size).toBe(4);
    });

    it('should handle root node', () => {
      const path = getPathToRoot('root1', testData);

      expect(path.has('root1')).toBe(true);
      expect(path.size).toBe(1);
    });

    it('should handle non-existent node', () => {
      const path = getPathToRoot('non-existent', testData);

      expect(path.has('non-existent')).toBe(true);
      expect(path.size).toBe(1);
    });

    it('should handle complex graph with cycles', () => {
      const path = getPathToRoot('G', complexData);

      expect(path.has('G')).toBe(true);
      expect(path.has('E')).toBe(true);
      expect(path.has('F')).toBe(true);
      expect(path.has('C')).toBe(true);
      expect(path.has('D')).toBe(true);
      expect(path.has('A')).toBe(true);
      expect(path.has('B')).toBe(true);
    });

    it('should handle empty data', () => {
      const path = getPathToRoot('test', []);

      expect(path.has('test')).toBe(true);
      expect(path.size).toBe(1);
    });

    it('should handle node without edges', () => {
      const singleNodeData = [[createTestNode('single')]];
      const path = getPathToRoot('single', singleNodeData);

      expect(path.has('single')).toBe(true);
      expect(path.size).toBe(1);
    });
  });

  describe('getAllChildren', () => {
    it('should find all children of root node', () => {
      const children = getAllChildren('root1', testData);

      expect(children.has('root1')).toBe(true);
      expect(children.has('child1')).toBe(true);
      expect(children.has('child2')).toBe(true);
      expect(children.has('grandchild1')).toBe(true);
      expect(children.has('grandchild2')).toBe(true);
      expect(children.has('great1')).toBe(true);
      expect(children.has('great2')).toBe(true);
      expect(children.size).toBe(7);
    });

    it('should find children of intermediate node', () => {
      const children = getAllChildren('child1', testData);

      expect(children.has('child1')).toBe(true);
      expect(children.has('grandchild1')).toBe(true);
      expect(children.has('grandchild2')).toBe(true);
      expect(children.has('great1')).toBe(true);
      expect(children.has('great2')).toBe(true);
      expect(children.size).toBe(5);
    });

    it('should handle leaf node', () => {
      const children = getAllChildren('great1', testData);

      expect(children.has('great1')).toBe(true);
      expect(children.size).toBe(1);
    });

    it('should handle non-existent node', () => {
      const children = getAllChildren('non-existent', testData);

      expect(children.has('non-existent')).toBe(true);
      expect(children.size).toBe(1);
    });

    it('should handle complex graph', () => {
      const children = getAllChildren('A', complexData);

      expect(children.has('A')).toBe(true);
      expect(children.has('C')).toBe(true);
      expect(children.has('D')).toBe(true);
      expect(children.has('E')).toBe(true);
      expect(children.has('F')).toBe(true);
      expect(children.has('G')).toBe(true);
      expect(children.size).toBe(6);
    });

    it('should handle empty data', () => {
      const children = getAllChildren('test', []);

      expect(children.has('test')).toBe(true);
      expect(children.size).toBe(1);
    });
  });

  describe('getSubGraphNodeSet', () => {
    it('should return node set including ancestors and descendants', () => {
      const subGraph = getSubGraphNodeSet('child1', testData);

      // Should include the node itself
      expect(subGraph.has('child1')).toBe(true);

      // Should include ancestors
      expect(subGraph.has('root1')).toBe(true);

      // Should include descendants
      expect(subGraph.has('grandchild1')).toBe(true);
      expect(subGraph.has('grandchild2')).toBe(true);
      expect(subGraph.has('great1')).toBe(true);
      expect(subGraph.has('great2')).toBe(true);

      expect(subGraph.size).toBe(6);
    });

    it('should handle root node', () => {
      const subGraph = getSubGraphNodeSet('root1', testData);

      expect(subGraph.has('root1')).toBe(true);
      expect(subGraph.has('child1')).toBe(true);
      expect(subGraph.has('child2')).toBe(true);
      expect(subGraph.has('grandchild1')).toBe(true);
      expect(subGraph.has('grandchild2')).toBe(true);
      expect(subGraph.has('great1')).toBe(true);
      expect(subGraph.has('great2')).toBe(true);
    });

    it('should handle leaf node', () => {
      const subGraph = getSubGraphNodeSet('great1', testData);

      expect(subGraph.has('great1')).toBe(true);
      expect(subGraph.has('grandchild1')).toBe(true);
      expect(subGraph.has('child1')).toBe(true);
      expect(subGraph.has('root1')).toBe(true);
      expect(subGraph.size).toBe(4);
    });

    it('should handle null/undefined data', () => {
      const subGraph = getSubGraphNodeSet('test', null as any);

      expect(subGraph.has('t')).toBe(true);
      expect(subGraph.has('e')).toBe(true);
      expect(subGraph.has('s')).toBe(true);
      expect(subGraph.size).toBe(3);
    });

    it('should handle complex graph with cycles', () => {
      const subGraph = getSubGraphNodeSet('E', complexData);

      // Should include all connected nodes
      expect(subGraph.has('E')).toBe(true);
      expect(subGraph.has('C')).toBe(true);
      expect(subGraph.has('D')).toBe(true);
      expect(subGraph.has('A')).toBe(true);
      expect(subGraph.has('B')).toBe(true);
      expect(subGraph.has('G')).toBe(true);

      expect(subGraph.has('F')).toBe(false);
      expect(subGraph.size).toBe(6);
    });
  });

  describe('createSubGraph', () => {
    it('should create filtered subgraph with only relevant nodes', () => {
      const subGraph = createSubGraph('child1', testDataset);

      expect(Array.isArray(subGraph)).toBe(true);
      expect(subGraph.length).toBeGreaterThan(0);

      // Check that only relevant nodes are included
      const allNodes = subGraph.flat();
      const nodeIds = allNodes.map(node => node.id);

      expect(nodeIds).toContain('child1');
      expect(nodeIds).toContain('root1');
      expect(nodeIds).toContain('grandchild1');
      expect(nodeIds).toContain('grandchild2');
      expect(nodeIds).toContain('great1');
      expect(nodeIds).toContain('great2');

      // Should not contain unrelated nodes
      expect(nodeIds).not.toContain('root2');
      expect(nodeIds).not.toContain('child3');
      expect(nodeIds).not.toContain('grandchild3');
    });

    it('should filter edges to only include subgraph nodes', () => {
      const subGraph = createSubGraph('child1', testDataset);
      const allNodes = subGraph.flat();

      // Check that edges only reference nodes in the subgraph
      allNodes.forEach(node => {
        if (node.edges) {
          const subGraphNodeIds = new Set(allNodes.map(n => n.id));
          node.edges.forEach(edgeId => {
            expect(subGraphNodeIds.has(edgeId)).toBe(true);
          });
        }
      });
    });

    it('should remove empty levels', () => {
      const subGraph = createSubGraph('great1', testDataset);

      // Each level should have at least one node
      subGraph.forEach(level => {
        expect(level.length).toBeGreaterThan(0);
      });
    });

    it('should handle root node subgraph', () => {
      const subGraph = createSubGraph('root1', testDataset);

      expect(subGraph.length).toBe(testDataset.data.length);

      const allNodes = subGraph.flat();
      const nodeIds = new Set(allNodes.map(node => node.id));

      expect(nodeIds.has('root1')).toBe(true);
      expect(nodeIds.has('child1')).toBe(true);
      expect(nodeIds.has('child2')).toBe(true);
    });

    it('should handle leaf node subgraph', () => {
      const subGraph = createSubGraph('great1', testDataset);

      const allNodes = subGraph.flat();
      const nodeIds = new Set(allNodes.map(node => node.id));

      expect(nodeIds.has('great1')).toBe(true);
      expect(nodeIds.has('grandchild1')).toBe(true);
      expect(nodeIds.has('child1')).toBe(true);
      expect(nodeIds.has('root1')).toBe(true);
    });

    it('should preserve node properties', () => {
      const subGraph = createSubGraph('child1', testDataset);
      const allNodes = subGraph.flat();
      const child1Node = allNodes.find(node => node.id === 'child1');

      expect(child1Node).toBeDefined();
      expect(child1Node?.markdown).toBe('Node child1');
      expect(child1Node?.icons).toEqual(['test-icon']);
    });

    it('should handle complex graphs with cycles', () => {
      const subGraph = createSubGraph('G', complexDataset);

      const allNodes = subGraph.flat();
      const nodeIds = new Set(allNodes.map(node => node.id));

      // Should include all connected nodes
      expect(nodeIds.has('G')).toBe(true);
      expect(nodeIds.has('E')).toBe(true);
      expect(nodeIds.has('F')).toBe(true);
      expect(nodeIds.has('C')).toBe(true);
      expect(nodeIds.has('D')).toBe(true);
      expect(nodeIds.has('A')).toBe(true);
      expect(nodeIds.has('B')).toBe(true);
    });

    it('should handle non-existent node', () => {
      const subGraph = createSubGraph('non-existent', testDataset);

      expect(Array.isArray(subGraph)).toBe(true);
      expect(subGraph.length).toBe(0);
    });

    it('should handle empty dataset', () => {
      const emptyDataset: NestedDataset = {
        id: 'empty',
        metadata: { type: 'nested' },
        data: []
      };

      const subGraph = createSubGraph('test', emptyDataset);

      expect(Array.isArray(subGraph)).toBe(true);
      expect(subGraph.length).toBe(0);
    });
  });

  describe('edge cases and error handling', () => {
    it('should handle nodes with circular references', () => {
      const circularData: RawEntry[][] = [[createTestNode('A', ['B']), createTestNode('B', ['A'])]];

      // Should not cause infinite loops
      expect(() => {
        getPathToRoot('A', circularData);
      }).not.toThrow();

      expect(() => {
        getAllChildren('A', circularData);
      }).not.toThrow();
    });

    it('should handle nodes with self-references', () => {
      const selfRefData: RawEntry[][] = [[createTestNode('A', ['A'])]];

      expect(() => {
        getPathToRoot('A', selfRefData);
      }).not.toThrow();

      expect(() => {
        getAllChildren('A', selfRefData);
      }).not.toThrow();
    });

    it('should handle deeply nested graphs', () => {
      const deepData: RawEntry[][] = [];
      for (let i = 0; i < 100; i++) {
        deepData.push([createTestNode(`node${i}`, i > 0 ? [`node${i - 1}`] : [])]);
      }

      expect(() => {
        getPathToRoot('node99', deepData);
      }).not.toThrow();

      expect(() => {
        getAllChildren('node0', deepData);
      }).not.toThrow();
    });

    it('should handle nodes with undefined or null edges', () => {
      const dataWithNulls: RawEntry[][] = [
        [
          { id: 'A', edges: undefined },
          { id: 'B', edges: null as any },
          { id: 'C' } // No edges property
        ]
      ];

      expect(() => {
        getPathToRoot('A', dataWithNulls);
        getPathToRoot('B', dataWithNulls);
        getPathToRoot('C', dataWithNulls);
      }).not.toThrow();
    });
  });
});
