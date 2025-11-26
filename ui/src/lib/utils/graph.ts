import type { NestedDataset, RawEntry } from 'lib/types/graph';

export const cyrb53 = (str: string, seed = 0) => {
  let h1 = 0xdeadbeef ^ seed,
    h2 = 0x41c6ce57 ^ seed;
  for (let i = 0, ch; i < str.length; i++) {
    ch = str.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507);
  h1 ^= Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507);
  h2 ^= Math.imul(h1 ^ (h1 >>> 13), 3266489909);

  return parseFloat(`0.${4294967296 * (2097151 & h2) + (h1 >>> 0)}`);
};

export const cssImportant = (property: string) => `${property} !important`;

const findNode = (nodeId: string, flatNodes: RawEntry[]) => {
  return flatNodes.find(node => node.id === nodeId);
};

export const getPathToRoot = (nodeId, data: RawEntry[][]) => {
  const getRoot = (currNodeId: string, results: Set<string>) => {
    if (results.has(currNodeId)) {
      return results;
    }
    let newResults = results.add(currNodeId);
    const currNode = findNode(currNodeId, data.flat());
    if (currNode?.edges) {
      currNode?.edges.forEach(parent => {
        newResults = getRoot(parent, results);
      });
    }
    return newResults;
  };

  return getRoot(nodeId, new Set<string>());
};

export const getAllChildren = (nodeId, data: RawEntry[][]) => {
  const getChildren = (currNodeId: string, results: Set<string>) => {
    if (results.has(currNodeId)) {
      return results;
    }
    let newResults = results.add(currNodeId);
    const currNode = findNode(currNodeId, data.flat());
    const directChildren = data.flat().filter(n => n.edges?.includes(currNode?.id));
    if (directChildren) {
      directChildren.forEach(child => {
        newResults = getChildren(child.id, newResults);
      });
    }
    return newResults;
  };

  return getChildren(nodeId, new Set<string>());
};

export const getSubGraphNodeSet = (nodeId: string, data: RawEntry[][]) => {
  if (!data) {
    return new Set<string>(nodeId);
  }
  const ancestors: Set<string> = getPathToRoot(nodeId, data);
  const descendents: Set<string> = getAllChildren(nodeId, data);
  return new Set<string>([nodeId, ...ancestors, ...descendents]);
};

export const createSubGraph = (nodeId: string, dataset: NestedDataset) => {
  const subGraphNodes = getSubGraphNodeSet(nodeId, dataset.data);
  const newData = dataset.data
    .map(level =>
      level
        .filter(node => subGraphNodes.has(node.id))
        .map(node => ({ ...node, edges: node?.edges?.filter(edge => subGraphNodes.has(edge)) }))
    )
    .filter(level => level.length > 0);
  return newData;
};
