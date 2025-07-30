import * as d3 from 'd3';
import useMyHighlights from 'lib/hooks/useMyHighlights';
import { useMyLocalStorageItem } from 'lib/hooks/useMyLocalStorage';
import type { NestedDataset } from 'lib/types/graph';
import { StorageKey } from 'lib/utils/constants';
import { cyrb53 } from 'lib/utils/graph';
import countBy from 'lodash-es/countBy';
import sumBy from 'lodash-es/sumBy';
import type { FC, MutableRefObject } from 'react';
import { memo, useCallback, useMemo, useRef } from 'react';
import Leaf from '../Leaf';

const DEFAULT_OPTIONS = {
  width: '100%',
  backgroundColor: 'grey',
  textColor: 'black',
  nodeColor: {
    border: 'black',
    center: 'white'
  },
  letterSize: 12,
  letterWidth: 8,
  nodeRadius: 8,
  lineWidth: 2,
  circlePadding: null // We'll make this dynamic
};

DEFAULT_OPTIONS.circlePadding = 3 * DEFAULT_OPTIONS.nodeRadius;

type Options = Partial<typeof DEFAULT_OPTIONS>;

const Cloud: FC<{
  svgRef?: MutableRefObject<SVGSVGElement>;
  graph: NestedDataset;
  options?: Options;
}> = ({ svgRef, graph, options = {} }) => {
  const {
    width,
    backgroundColor,
    textColor,
    letterSize,
    letterWidth,
    circlePadding,
    nodeRadius,
    nodeColor,
    lineWidth
  } = {
    ...DEFAULT_OPTIONS,
    ...options
  };

  const { onNodeHoveredChanged, onNodeClicked, nodeOpacities, highlightedPath } = useMyHighlights(graph);

  const [colorScheme] = useMyLocalStorageItem(StorageKey.COLOR_SCHEME, 'Spectral');

  const currentX = useRef(2 * nodeRadius);
  const currentY = useRef(letterSize + nodeRadius);
  const nodeLocations = useRef<{ [id: string]: [number, number, number] }>({});

  /**
   * Processed levels, adding the level index to each node
   */
  const nodes = useMemo(
    () =>
      graph.data.flatMap((cloud, cloudIndex) =>
        cloud.map(node => ({
          ...node,
          cloud: cloudIndex.toString()
        }))
      ),
    [graph.data]
  );

  const clouds = useMemo(() => countBy(nodes, node => node.cloud), [nodes]);

  const colors = useMemo(
    () =>
      d3.scaleOrdinal(
        Object.keys(clouds).map(cloud => (d3[`interpolate${colorScheme}`] ?? d3.interpolateSpectral)(cyrb53(cloud)))
      ),
    [clouds, colorScheme]
  );

  const links = useMemo(
    () =>
      nodes.flatMap(node =>
        (node?.edges ?? []).map(parent => ({
          source: node.id,
          target: parent
        }))
      ),
    [nodes]
  );

  const pack = useMemo(() => d3.pack().size([600, 600]).padding(circlePadding), [circlePadding]);

  const cloudLocations: d3.HierarchyCircularNode<{ id: string; value: number }>[] = useMemo(() => {
    const data = Object.entries(clouds).map(([id]) => ({
      id,
      children: nodes
        .filter(node => node.cloud === id)
        .map(node => ({
          ...node,
          value: 1
        }))
    }));

    return pack(
      d3.hierarchy({ children: data }).sum((d: any) => (d.children ? sumBy(d.children, (c: any) => c.value) : d.value))
    ).children as any;
  }, [clouds, nodes, pack]);

  const opacities = useCallback(
    (link: { source: string; target: string }) =>
      highlightedPath.size === 0 || (highlightedPath.has(link.source) && highlightedPath.has(link.target)) ? 1 : 0.2,
    [highlightedPath]
  );

  currentX.current = 2 * nodeRadius;
  currentY.current = letterSize + nodeRadius;
  nodeLocations.current = {};

  return (
    <svg id="viz" ref={svgRef} width={width} height={600} style={{ backgroundColor }}>
      <g id="view">
        {cloudLocations.map(cloud => (
          <g key={cloud.data.id}>
            <circle cx={cloud.x} cy={cloud.y} r={cloud.r} strokeWidth={4} stroke={colors(cloud.data.id)} fill="none" />
          </g>
        ))}
        {links.map(link => {
          const source = cloudLocations.flatMap(c => c.children).find(node => node.data.id === link.source);
          const target = cloudLocations.flatMap(c => c.children).find(node => node.data.id === link.target);

          return (
            <g key={source.data.id + target.data.id}>
              <path
                d={`M ${source.x} ${source.y} L ${target.x} ${target.y}`}
                stroke="black"
                strokeWidth={lineWidth + 3}
                strokeOpacity={opacities(link)}
              />
              <path
                d={`M ${source.x} ${source.y} L ${target.x} ${target.y}`}
                stroke="white"
                strokeWidth={lineWidth}
                strokeOpacity={opacities(link)}
              />
            </g>
          );
        })}
        {cloudLocations.map(cloud => (
          <g key={cloud.id}>
            {cloud.children.map(node => (
              <Leaf
                key={node.data.id}
                nodeId={node.data.id}
                height={0}
                x={node.x}
                y={node.y}
                nodeRadius={nodeRadius}
                nodeColor={nodeColor}
                nodeOpacity={nodeOpacities(node.data.id)}
                letterSize={letterSize}
                letterWidth={letterWidth}
                textColor={textColor}
                onHoverChanged={onNodeHoveredChanged}
                onClick={onNodeClicked}
              />
            ))}
          </g>
        ))}
      </g>
    </svg>
  );
};

export default memo(Cloud);
