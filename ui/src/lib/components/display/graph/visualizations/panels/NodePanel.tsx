import { Skeleton } from '@mui/material';
import type { RawEntry } from 'lib/types/graph';
import type { FC } from 'react';
import NodeCard from '../../elements/NodeCard';

const NodePanel: FC<{
  selectedNodeIds: string[];
  findNode: (id: string) => RawEntry;
}> = ({ selectedNodeIds, findNode }) => {
  return (
    <>
      {selectedNodeIds
        .map(selectedNodeId => findNode(selectedNodeId))
        .filter(node => !!node)
        .map(node => (
          <NodeCard key={node.id} node={node} />
        ))}
      {selectedNodeIds.length < 1 && <Skeleton variant="rounded" height={150} />}
    </>
  );
};

export default NodePanel;
