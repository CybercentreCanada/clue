import type { NestedDataset } from 'lib/types/graph';
import { getSubGraphNodeSet } from 'lib/utils/graph';
import { safeAddEventListener } from 'lib/utils/window';
import { useCallback, useEffect, useMemo, useState } from 'react';

const useMyHighlights = (graph: NestedDataset, onNodeSelectionChanged?: (nodeIds: string[]) => void) => {
  const data = useMemo(() => graph?.data, [graph]);

  const [hoveredNode, setHoveredNode] = useState<string>();
  const [highlightedNodes, setHighlightedNodes] = useState<Set<string>>(new Set());
  const [highlightedPath, setHighlightedPath] = useState<Set<string>>(new Set());
  const [ctrlKeyDown, setCtrlKeyDown] = useState<boolean>();

  const onKeyPressed = useCallback((ev: KeyboardEvent) => {
    setCtrlKeyDown(ev.ctrlKey);
  }, []);

  const onKeyUnpressed = useCallback((ev: KeyboardEvent) => {
    setCtrlKeyDown(ev.ctrlKey);
  }, []);

  useEffect(() => {
    return safeAddEventListener('keydown', onKeyPressed);
  }, [onKeyPressed]);

  useEffect(() => {
    return safeAddEventListener('keyup', onKeyUnpressed);
  }, [onKeyUnpressed]);

  const onNodeHoveredChanged = useCallback((nodeId: string, isHovered: boolean) => {
    if (isHovered) {
      setHoveredNode(nodeId);
    } else {
      setHoveredNode('');
    }
  }, []);

  const onNodeClicked = useCallback(
    (nodeId: string, isSelected: boolean, event: MouseEvent) => {
      let newHighlightedNodes = new Set<string>();
      if (isSelected) {
        newHighlightedNodes = new Set<string>(event.ctrlKey ? [...highlightedNodes, nodeId] : [nodeId]);
      } else {
        newHighlightedNodes = event.ctrlKey ? new Set<string>([...highlightedNodes]) : new Set<string>();
        newHighlightedNodes.delete(nodeId);
      }
      setHighlightedNodes(newHighlightedNodes);
      onNodeSelectionChanged?.([...newHighlightedNodes]);
    },
    [highlightedNodes, onNodeSelectionChanged]
  );

  const nodeOpacities = useCallback(
    (nodeId: string) => {
      return highlightedPath.size === 0 || highlightedPath.has(nodeId) ? 1 : 0.2;
    },
    [highlightedPath]
  );

  useEffect(() => {
    let newHighlightedPath = new Set<string>();
    if (hoveredNode) {
      const subGraphNodes = getSubGraphNodeSet(hoveredNode, data);
      newHighlightedPath = new Set<string>([...newHighlightedPath, ...subGraphNodes]);
    }
    if (highlightedNodes.size && (ctrlKeyDown || !hoveredNode)) {
      highlightedNodes.forEach(highlightedNode => {
        const subGraphNodes = getSubGraphNodeSet(highlightedNode, data);
        newHighlightedPath = new Set<string>([...newHighlightedPath, ...subGraphNodes]);
      });
    }
    setHighlightedPath(newHighlightedPath);
  }, [hoveredNode, highlightedNodes, ctrlKeyDown, data]);

  return {
    onNodeHoveredChanged,
    onNodeClicked,
    nodeOpacities,
    highlightedPath,
    highlightedNodes,
    hoveredNode
  };
};

export default useMyHighlights;
