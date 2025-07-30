import { Box, colors, useTheme } from '@mui/material';
import useComparator from 'lib/hooks/useComparator';
import useMyHighlights from 'lib/hooks/useMyHighlights';
import { useMyLocalStorageItem } from 'lib/hooks/useMyLocalStorage';
import type { NestedDataset, ZoomField } from 'lib/types/graph';
import { BUNDLE_SEPARATOR, StorageKey } from 'lib/utils/constants';
import cloneDeep from 'lodash-es/cloneDeep';
import get from 'lodash-es/get';
import isNil from 'lodash-es/isNil';
import max from 'lodash-es/max';
import range from 'lodash-es/range';
import sum from 'lodash-es/sum';
import type { FC, MutableRefObject, ReactNode } from 'react';
import { memo, useMemo } from 'react';
import NodeCard from '../../elements/NodeCard';
import getIcon from '../icons';
import Leaf from '../Leaf';
import BundleLine from './BundleLine';
import type { Bundle, Node } from './types';

interface TreeOptions {
  textColor: string;
  nodeColor: {
    border: string;
    center: string;
  };
  letterSize: number;
  letterWidth: number;
  xSpacing: number;
  ySpacing: number;
  nodeRadius: number;
  maxArcRadius: number;
  linePaddingX: number;
  linePaddingY: number;
  lineWidth: number;
  enableEntryPadding: boolean;
  truncateLabels: boolean;
  enableTimestamps: boolean;
  rowStep: number;
  belowPrevious: boolean;
  iconOrientation: 'horizontal' | 'vertical';
  lineDirection: 'horizontal' | 'vertical';
  colorTheme?: string;
}

const DEFAULT_OPTIONS: TreeOptions = {
  textColor: 'white',
  nodeColor: {
    border: 'grey',
    center: 'white'
  },
  letterSize: 10,
  letterWidth: 6.5,
  xSpacing: 8,
  ySpacing: 20,
  nodeRadius: 6,
  maxArcRadius: 8,
  linePaddingX: 10,
  linePaddingY: 10,
  lineWidth: 3,
  enableEntryPadding: true,
  truncateLabels: true,
  enableTimestamps: true,
  iconOrientation: 'vertical',
  lineDirection: 'horizontal',
  rowStep: null, // We'll make this dynamic
  belowPrevious: false
};

// DEFAULT_OPTIONS.rowStep = DEFAULT_OPTIONS.ySpacing * 4;
DEFAULT_OPTIONS.rowStep = DEFAULT_OPTIONS.ySpacing * 2;

const Tree: FC<{
  svgRef?: MutableRefObject<SVGSVGElement>;
  graph: NestedDataset;
  labelKeys: ZoomField[];
  onNodeSelectionChanged: (nodeIds: string[]) => void;
  options?: Partial<TreeOptions>;
  zoom: d3.ZoomTransform;
}> = ({ svgRef, graph, labelKeys, onNodeSelectionChanged, zoom, options = {} }) => {
  const combinedOptions = useMemo(
    () => ({
      ...DEFAULT_OPTIONS,
      ...options,
      ...(graph?.metadata.display?.visualization?.config ?? {})
    }),
    [graph?.metadata.display?.visualization?.config, options]
  );

  const {
    xSpacing: baseXSpacing,
    ySpacing: baseYSpacing,
    linePaddingX: baseLinePaddingX,
    linePaddingY: baseLinePaddingY
  }: Partial<TreeOptions> = combinedOptions;

  const { runComparators, runComparator } = useComparator();
  const { onNodeHoveredChanged, onNodeClicked, nodeOpacities, highlightedPath, highlightedNodes, hoveredNode } =
    useMyHighlights(graph, nodeIds => onNodeSelectionChanged(nodeIds));

  const theme = useTheme();
  const isDark = useMemo(() => theme.palette.mode === 'dark', [theme]);

  const [showCardsSettings] = useMyLocalStorageItem(StorageKey.SHOW_CARDS, false);
  const [cardCutoff] = useMyLocalStorageItem(StorageKey.CARD_CUTOFF, 2.5);

  const showCards = useMemo(() => zoom.k > cardCutoff && showCardsSettings, [cardCutoff, showCardsSettings, zoom.k]);

  /**
   * Processed levels, adding the level index to each node
   */
  const levels: Node[][] = useMemo(
    () =>
      graph.data.map((level, levelIndex) =>
        level.map(node => ({
          ...node,
          parents: node?.edges,
          level: levelIndex
        }))
      ),
    [graph.data]
  );

  const flatNodes = useMemo(() => levels.flat(), [levels]);

  const [xSpacing, linePaddingX, ySpacing, linePaddingY] = useMemo(() => {
    const baseValues = [
      [baseXSpacing, baseLinePaddingX],
      [baseYSpacing, baseLinePaddingY]
    ];

    if (zoom.k > 1 && showCardsSettings) {
      return baseValues.flatMap((arr, index) =>
        arr.map(_v => _v * Math.pow(2.5 - index * 1.25, Math.min(zoom.k, 2.5) - 1))
      ) as [number, number, number, number];
    } else {
      return baseValues.flat() as [number, number, number, number];
    }
  }, [baseLinePaddingX, baseLinePaddingY, baseXSpacing, baseYSpacing, showCardsSettings, zoom.k]);

  let portBounds;
  if (!graph || !svgRef.current) {
    portBounds = [
      [0, 0],
      [0, 0]
    ];
  } else {
    const data = svgRef.current.getBoundingClientRect();
    portBounds = [zoom.invert([0, 0]), zoom.invert([data.width, data.height])];
  }

  /**
   * Bundles are groups of paths between
   */
  const bundles = useMemo(() => {
    const bundlesDict: { [key: string]: Bundle } = {};

    flatNodes.forEach(node => {
      if (!node.parents) {
        return;
      }

      // we generate the bundle id based on the parents of the node
      const bundleId = node.parents.join(BUNDLE_SEPARATOR);

      if (bundlesDict[bundleId]) {
        bundlesDict[bundleId].destinations.push(node);
      } else {
        bundlesDict[bundleId] = {
          id: bundleId,
          sources: node.parents.map(parent => flatNodes.find(_node => _node.id === parent)),
          destinations: [node]
        };
      }
    });

    return Object.values(bundlesDict);
  }, [flatNodes]);

  const layoutData = useMemo(() => {
    const {
      letterSize,
      letterWidth,
      enableEntryPadding,
      truncateLabels,
      rowStep,
      belowPrevious
    }: Partial<TreeOptions> = combinedOptions;

    let currentX = 0;
    let currentY = 0;
    const nodeLocations: { [id: string]: [number, number, number] } = {};
    const linesByLevel: { [level: number]: Set<string> } = {};
    const paddingByLevel: { [level: number]: number } = {};
    const inputs: { [id: string]: Set<string> } = {};
    const outputs: { [id: string]: Set<string> } = {};

    // First pass at generating the locations of the nodes. We start by just placing them assuming no connections
    // We'll mutate the nodeLocations ref throughout the rendering process
    levels.forEach((level, levelIndex) => {
      let longestLabel = 0;
      level.forEach(node => {
        const validKeys = labelKeys?.filter(_comparator => runComparator(_comparator, node));
        const labelKey = validKeys?.pop()?.label;

        const labelRows =
          labelKey
            ?.split(',')
            .map(key => get(node, key))
            .filter(val => !!val) ?? [];

        if (labelRows.length < 1) {
          node.id.split('\n').forEach(line => labelRows.push(line));
        }

        const labelHeight = labelRows.length * letterSize;
        currentY += labelHeight;
        //                               [x, y, height] we set height to a negative number so it's calculated correctly later on
        nodeLocations[node.id] = [+currentX, +currentY, -linePaddingY];
        // We move each node down by a certain amount
        currentY += ySpacing;

        if (enableEntryPadding) {
          longestLabel = Math.max(longestLabel, max(labelRows?.map(row => row.toString().length) ?? [node.id.length]));
        }
      });

      // Shift to the next level
      currentX += xSpacing + (!truncateLabels ? longestLabel : Math.min(longestLabel, 44)) * letterWidth;
      // Reset the Y coordinate to a new row, dropping it down each time
      if (!belowPrevious) {
        currentY = (levelIndex + 1) * rowStep;
      } else {
        currentY += rowStep;
      }
    });

    // Layout updates based on bundle formatting
    bundles.forEach(bundle => {
      bundle.sources.forEach(source => {
        // For each bundle leaving a node, increment the height of the node
        // This is where height gets set to 0 if there's only one node leaving it
        if (!outputs[source.id]) {
          outputs[source.id] = new Set();
        }
        outputs[source.id].add(bundle.id);
      });

      // In order to track the number of lines that'll be rendered on each line, we track a set of all
      // bundles creating lines at each level. We'll use this for layout updates later
      bundle.destinations.forEach(dest => {
        if (isNil(linesByLevel[dest.level])) {
          linesByLevel[dest.level] = new Set();
        }

        if (!inputs[dest.id]) {
          inputs[dest.id] = new Set();
        }

        linesByLevel[dest.level].add(bundle.id);
        inputs[dest.id].add(bundle.id);
      });
    });

    // For convenience, we also store the line padding. This essentially gives us a static "max" we use later,
    // as the other will drop as the layout is rendered
    Object.entries(linesByLevel).forEach(([level, lines]) => (paddingByLevel[level] = lines.size));

    // Deal with X location
    levels.forEach((level, levelIndex) => {
      // calculate the total padding adding to level x by calculating the padding for all preceding levels
      const indexesSoFar = range(levelIndex + 1);
      const paddingArray = indexesSoFar.map(_levelIndex => paddingByLevel[_levelIndex] ?? 0);
      const totalPadding = sum(paddingArray) * linePaddingX;

      level.forEach(node => {
        // Add that to each note
        nodeLocations[node.id][0] += totalPadding;
      });
    });

    // Deal with Height
    flatNodes.forEach(node => {
      let maxHeight = max([inputs[node.id]?.size - 1, outputs[node.id]?.size - 1, 0]) * linePaddingY;
      if (inputs[node.id]?.has(node.id)) {
        maxHeight += linePaddingY;
      }

      nodeLocations[node.id][2] = maxHeight;

      const levelIndex = levels[node.level].findIndex(_node => _node.id === node.id);
      levels[node.level]
        .filter((__, index) => levelIndex < index)
        // For each node after the node we've made taller, move it down a bit so they don't overlap
        .forEach(_node => {
          nodeLocations[_node.id][1] += maxHeight;
        });
    });

    return {
      nodeLocations,
      linesByLevel,
      paddingByLevel
    };
  }, [
    bundles,
    combinedOptions,
    flatNodes,
    labelKeys,
    levels,
    linePaddingX,
    linePaddingY,
    runComparator,
    xSpacing,
    ySpacing
  ]);

  const [timestamps, bundleElements, nodes] = useMemo(() => {
    const {
      textColor,
      letterSize,
      letterWidth,
      nodeRadius,
      nodeColor,
      maxArcRadius,
      lineWidth,
      truncateLabels,
      enableTimestamps,
      belowPrevious,
      iconOrientation,
      lineDirection,
      colorTheme
    }: Partial<TreeOptions> = combinedOptions;

    const { nodeLocations, linesByLevel, paddingByLevel } = layoutData;

    const _nodes: ReactNode[] = [];
    const _timestamps: ReactNode[] = [];

    flatNodes.forEach(node => {
      const [x, y, _height] = nodeLocations[node.id];

      const labelKey = labelKeys?.filter(_comparator => runComparator(_comparator, node)).pop()?.label ?? 'id';

      let label = labelKey
        ?.split(',')
        .map(key => {
          let labelSection = get(node, key);
          if (labelSection && truncateLabels && labelSection.length > 44) {
            labelSection = labelSection.replace(/^(.{32}).+$/, '$1 (TRUNCATED)');
          }
          return labelSection;
        })
        .filter(section => !!section)
        .join('\n');

      if (!label) {
        if (node.id.length > 44) {
          label = node.id.replace(/^(.{32}).+$/, '$1 (TRUNCATED)');
        } else {
          label = node.id;
        }
      }

      if (belowPrevious && enableTimestamps && (node.timestamp || node.annotation)) {
        _timestamps.push(
          <g
            key={node.id + '-timestamp'}
            style={{
              cursor: 'default',
              fontFamily: '"Lucida Console", monospace',
              fontSize: letterSize * 0.75 + 'px'
            }}
          >
            <text
              x={portBounds[0][0] + xSpacing}
              y={y + (_height + nodeRadius) / 2}
              fill={theme.palette.getContrastText(theme.palette.background.paper)}
              style={{
                fillOpacity: nodeOpacities(node.id) / 2,
                transition: theme.transitions.create(['fill-opacity'], {
                  duration: theme.transitions.duration.short
                })
              }}
            >
              {node.timestamp}
            </text>
            {node.annotation &&
              node.annotation.split('\n').map((line, index) => (
                <text
                  key={line}
                  x={portBounds[0][0] + (node.timestamp?.length ?? 0) * letterWidth}
                  y={y + (_height + nodeRadius) / 2 + index * letterSize}
                  fill={isDark ? colors.orange[300] : colors.blue[900]}
                  style={{
                    fillOpacity: nodeOpacities(node.id),
                    transition: theme.transitions.create(['fill-opacity'], {
                      duration: theme.transitions.duration.short
                    })
                  }}
                >
                  {line}
                </text>
              ))}
          </g>
        );
      }

      if (!showCards) {
        const style = runComparators(
          graph.metadata.display?.styles?.filter(comparator => comparator.type === 'node'),
          node
        );

        const nodeOpacity = nodeOpacities(node.id);

        const icons = node.icons
          ?.map(icon => [icon, getIcon(icon)])
          .filter(([__, icon]) => !!icon)
          .map(([icon, Icon], index) => (
            <Icon
              key={icon}
              x={x - nodeRadius * 3 * (iconOrientation === 'horizontal' ? index + 1 : 0)}
              y={y - nodeRadius * 3 * (iconOrientation === 'vertical' ? index + 1 : 0)}
              size={letterSize * 1.5}
              style={{
                fillOpacity: nodeOpacity
              }}
              circleStyle={{
                fillOpacity: nodeOpacity
              }}
            />
          ));

        _nodes.push(
          <Leaf
            alwaysShowText
            key={node.id}
            nodeId={node.id}
            label={label}
            height={_height}
            x={x}
            y={y}
            style={style}
            nodeRadius={nodeRadius}
            nodeColor={nodeColor}
            nodeOpacity={nodeOpacity}
            letterSize={letterSize}
            letterWidth={letterWidth}
            textColor={textColor}
            selected={highlightedNodes.has(node.id)}
            onHoverChanged={onNodeHoveredChanged}
            onClick={onNodeClicked}
          >
            {icons}
          </Leaf>
        );
      }
    });

    const readonlyNodeLocations = cloneDeep(nodeLocations);
    const outputsByNode: { [id: string]: Set<string> } = {};
    const inputsByNode: { [id: string]: Set<string> } = {};
    const _bundleElements = bundles.map(bundle => {
      return (
        <BundleLine
          key={bundle.id}
          lineDirection={lineDirection}
          linesByLevel={linesByLevel}
          paddingByLevel={paddingByLevel}
          nodeLocations={readonlyNodeLocations}
          outputsByNode={outputsByNode}
          inputsByNode={inputsByNode}
          bundle={bundle}
          maxArcRadius={maxArcRadius}
          lineWidth={lineWidth}
          linePaddingX={linePaddingX}
          linePaddingY={linePaddingY}
          highlightedPath={highlightedPath}
          colorTheme={colorTheme}
        />
      );
    });

    return [_timestamps, _bundleElements, _nodes];
  }, [
    bundles,
    combinedOptions,
    graph.metadata.display?.styles,
    flatNodes,
    highlightedNodes,
    highlightedPath,
    isDark,
    labelKeys,
    layoutData,
    linePaddingX,
    linePaddingY,
    nodeOpacities,
    onNodeClicked,
    onNodeHoveredChanged,
    portBounds,
    runComparator,
    runComparators,
    showCards,
    theme.palette,
    theme.transitions,
    xSpacing
  ]);

  const cards = useMemo(() => {
    const { nodeRadius, lineWidth }: Partial<TreeOptions> = combinedOptions;

    const { nodeLocations } = layoutData;

    return flatNodes
      .filter(node => showCards || hoveredNode === node.id)
      .map(node => {
        const [x, y] = nodeLocations[node.id];

        return (
          <Box
            key={node.id}
            onMouseOver={() => onNodeHoveredChanged(node.id, true)}
            onMouseLeave={() => setTimeout(() => onNodeHoveredChanged(node.id, false), 100)}
            sx={{
              position: 'absolute',
              left: zoom.k * x + zoom.x,
              top: zoom.k * y + zoom.y,
              transform: `translateX(-${nodeRadius * 2}px) translateY(${lineWidth}px)`,
              backgroundColor: theme.palette.background.paper,
              maxWidth: '450px',
              maxHeight: '500px',
              overflow: 'auto'
            }}
          >
            <NodeCard node={node} />
          </Box>
        );
      });
  }, [
    combinedOptions,
    flatNodes,
    hoveredNode,
    layoutData,
    onNodeHoveredChanged,
    showCards,
    theme.palette.background.paper,
    zoom.k,
    zoom.x,
    zoom.y
  ]);

  return (
    <>
      <svg id="viz" ref={svgRef}>
        <g id="view">
          {timestamps}
          {bundleElements}
          {nodes}
        </g>
      </svg>
      {cards}
    </>
  );
};

export default memo(Tree);
