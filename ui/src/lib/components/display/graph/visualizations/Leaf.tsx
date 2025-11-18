import isNumber from 'lodash-es/isNumber';
import type { CSSProperties, FC, PropsWithChildren } from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';

const DEFAULT_NODE_RADIUS = 10;

interface LeafPropsType {
  nodeId: string;
  label?: string;
  x: number;
  y: number;
  height: number;
  nodeRadius: number;
  nodeColor: {
    border: string;
    center: string;
  };
  nodeOpacity: number;
  letterSize: number;
  letterWidth: number;
  textColor: string;
  selected?: boolean;
  alwaysShowText?: boolean;
  style?: CSSProperties;
  onHoverChanged?: (nodeId: string, isHovered: boolean) => void;
  onClick?: (nodeId: string, isSelected: boolean, event: MouseEvent) => void;
}

const Leaf: FC<PropsWithChildren<LeafPropsType>> = ({
  nodeId,
  label = nodeId,
  x,
  y,
  height,
  nodeRadius = DEFAULT_NODE_RADIUS,
  nodeColor,
  nodeOpacity = 1,
  letterSize,
  letterWidth,
  textColor,
  style = {},
  selected = false,
  alwaysShowText = false,
  onHoverChanged,
  onClick,
  children
}) => {
  const [isSelected, setIsSelected] = useState(selected);
  const [isHovered, setIsHovered] = useState(false);

  const classNames = useMemo(() => {
    const _classNames = ['node'];

    if (isHovered) {
      _classNames.push('hover');
    }

    if (isSelected) {
      _classNames.push('selected');
    }

    return _classNames;
  }, [isHovered, isSelected]);

  const handleOnClick = useCallback(
    event => {
      onClick?.(nodeId, !isSelected, event);
      setIsSelected(!isSelected);
    },
    [nodeId, onClick, isSelected]
  );

  const handleOnHoverChanged = useCallback(
    (value: boolean) => {
      setIsHovered(value);
      onHoverChanged?.(nodeId, value);
    },
    [nodeId, onHoverChanged]
  );

  useEffect(() => setIsSelected(selected), [selected]);

  let strokeWidth = `${nodeRadius}px`;
  if (style.strokeWidth) {
    if (isNumber(style.strokeWidth)) {
      strokeWidth = `${nodeRadius * style.strokeWidth}px`;
    } else {
      strokeWidth = style.strokeWidth;
    }
  }

  return (
    <g
      key={nodeId}
      id={'node-' + nodeId.replace(/[^A-Za-z0-9]*/g, '')}
      style={{ strokeLinecap: 'round' }}
      className={classNames.join(' ')}
      onClick={handleOnClick}
      onMouseOver={() => handleOnHoverChanged(true)}
      onMouseLeave={() => handleOnHoverChanged(false)}
    >
      {children}
      <path
        key={nodeId + '-border'}
        className="border"
        d={`M ${x} ${y} L ${x} ${y + Math.max(height, 0)}`}
        style={{
          strokeOpacity: nodeOpacity,
          ...style,
          strokeWidth: `calc(${strokeWidth} * 2)`,
          stroke: style.stroke ?? nodeColor.border
        }}
      />
      <path
        key={nodeId + '-middle'}
        className="center"
        d={`M ${x} ${y} L ${x} ${y + Math.max(height, 0)}`}
        style={{
          strokeOpacity: nodeOpacity,
          ...style,
          strokeWidth,
          stroke: style.fill ?? nodeColor.center
        }}
      />
      {(isHovered || alwaysShowText) &&
        label
          .split('\n')
          .reverse()
          .map((_label, index, arr) => (
            <text
              key={nodeId + '-label-' + _label}
              x={x + letterWidth}
              y={y - letterSize / 2 + arr.length - index * letterSize}
              fill={textColor}
              style={{
                cursor: 'default',
                fontFamily: '"Lucida Console", monospace',
                fontSize: letterSize + 'px',
                fillOpacity: nodeOpacity
              }}
            >
              {_label}
            </text>
          ))}
    </g>
  );
};

export default Leaf;
