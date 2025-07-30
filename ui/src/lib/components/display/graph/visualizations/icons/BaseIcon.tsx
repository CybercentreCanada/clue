import type { CSSProperties, FC, SVGProps } from 'react';
import { useMemo } from 'react';

const DEFAULTS = {
  size: 20
};

export interface IconProps extends SVGProps<SVGSVGElement> {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  size?: number;
  circleStyle?: CSSProperties;
}

const BaseIcon: FC<IconProps> = props => {
  const { width, height, size } = {
    ...DEFAULTS,
    ...props
  };

  const x = (props.x ?? 0) - (width ?? size) / 2;
  const y = (props.y ?? 0) - (height ?? size) / 2;

  const trimmedProps = useMemo(() => {
    const _props = { ...props };

    delete _props.circleStyle;

    return _props;
  }, [props]);

  return (
    <g>
      <circle cx={props.x} cy={props.y} r={size / 2} style={props.circleStyle ?? {}} />
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 -960 960 960"
        width={width ?? size}
        height={height ?? size}
        {...trimmedProps}
        x={x}
        y={y}
      >
        {props.children}
      </svg>
    </g>
  );
};

export default BaseIcon;
