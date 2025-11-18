import { useTheme } from '@mui/material';
import * as d3 from 'd3';
import { useMyLocalStorageItem } from 'lib/hooks/useMyLocalStorage';
import { StorageKey } from 'lib/utils/constants';
import { buildHorizontalLine, buildVerticalLine } from 'lib/utils/line';
import isNil from 'lodash-es/isNil';
import type { FC } from 'react';
import { useMemo } from 'react';
import { cyrb53 } from '../../../../../utils/graph';
import type { Bundle } from './types';

const BundleLine: FC<{
  bundle: Bundle;
  linesByLevel: { [level: number]: Set<string> };
  paddingByLevel: { [level: number]: number };
  nodeLocations: { [id: string]: [number, number, number] };
  inputsByNode: { [id: string]: Set<string> };
  outputsByNode: { [id: string]: Set<string> };
  lineWidth: number;
  linePaddingX: number;
  linePaddingY: number;
  maxArcRadius: number;
  highlightedPath: Set<string>;
  lineDirection: 'horizontal' | 'vertical';
  colorTheme?: string;
}> = ({
  bundle,
  linesByLevel,
  paddingByLevel,
  maxArcRadius,
  lineWidth,
  linePaddingX,
  linePaddingY,
  highlightedPath,
  nodeLocations,
  inputsByNode,
  outputsByNode,
  lineDirection,
  colorTheme
}) => {
  const theme = useTheme();
  const [colorSetting] = useMyLocalStorageItem(StorageKey.COLOR_SCHEME, 'Spectral');
  const [forceColorSetting] = useMyLocalStorageItem(StorageKey.FORCE_COLOR_SETTING, 'Spectral');

  const colorScheme = useMemo(
    () => (forceColorSetting ? colorSetting : colorTheme || colorSetting),
    [colorSetting, colorTheme, forceColorSetting]
  );

  // We'll generate colors based on a hash of the bundle ID
  const color = useMemo(
    () => (d3[`interpolate${colorScheme}`] ?? d3.interpolateSpectral)(cyrb53(JSON.stringify(bundle))),
    [bundle, colorScheme]
  );

  const opacities = useMemo(
    () => (_bundle: Bundle) =>
      highlightedPath.size === 0 ||
      (_bundle.sources.some(source => highlightedPath.has(source.id)) &&
        _bundle.destinations.some(destination => highlightedPath.has(destination.id)))
        ? 1
        : 0.2,
    [highlightedPath]
  );

  const arrows = [];

  // Each bundle will have a group of paths representing the path from every source to every destination
  // TODO: Make this a bit better - there's occasional visual artifacts
  const d = bundle.sources
    .flatMap(source => {
      const result = bundle.destinations.flatMap(dest => {
        linesByLevel[dest.level].delete(bundle.id);

        // Get the parent, child position and dimensions
        const [parentX, rawParentY] = nodeLocations[source.id];
        const parentY = rawParentY + (outputsByNode[source.id]?.size ?? 0) * linePaddingY;

        const [childX, rawChildY, childHeight] = nodeLocations[dest.id];
        const childY = rawChildY + (inputsByNode[dest.id]?.size ?? 0 + +(source.id === dest.id)) * linePaddingY;

        const distanceX = childX - parentX;
        const distanceY = childY - parentY;

        const arcRadius = Math.min(Math.abs(distanceY / 3), maxArcRadius);

        // We use lines and arcs to generate pretty dependency graphs
        // https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Paths#line_commands
        // https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Paths#curve_commands
        if (lineDirection === 'horizontal') {
          return buildHorizontalLine({
            paddingAtLevel: paddingByLevel[dest.level],
            numLines: linesByLevel[dest.level].size,
            nodeLocations,
            dest,
            distanceX,
            distanceY,
            childX,
            childY,
            childHeight,
            parentX,
            parentY,
            linePaddingX,
            arcRadius
          });
        } else {
          return buildVerticalLine({
            paddingAtLevel: paddingByLevel[dest.level],
            numLines: linesByLevel[dest.level].size,
            distanceX,
            distanceY,
            childX,
            childY,
            childHeight,
            parentX,
            parentY,
            linePaddingX,
            arcRadius
          });
        }
      });

      return result;
    })
    .join('\n');

  bundle.destinations.forEach(dest => {
    if (isNil(inputsByNode[dest.id])) {
      inputsByNode[dest.id] = new Set();
    }

    inputsByNode[dest.id].add(bundle.id);
  });

  bundle.sources.forEach(source => {
    if (isNil(outputsByNode[source.id])) {
      outputsByNode[source.id] = new Set();
    }

    outputsByNode[source.id].add(bundle.id);
  });

  return (
    <g key={bundle.id} className="path" style={{ opacity: opacities(bundle) }}>
      <path
        key={bundle.id + '-bg'}
        d={d}
        style={{ fill: 'none', stroke: theme.palette.background.paper, strokeWidth: lineWidth + 3 }}
      />
      <path
        key={bundle.id + '-fg'}
        d={d}
        strokeWidth={lineWidth}
        style={{ fill: 'none', stroke: color, strokeWidth: lineWidth }}
      />
      {arrows}
    </g>
  );
};

export default BundleLine;
