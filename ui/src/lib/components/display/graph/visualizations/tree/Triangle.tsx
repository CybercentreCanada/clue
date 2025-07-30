import { useTheme } from '@mui/material';
import type { FC } from 'react';

const Triangle: FC<{
  x: number;
  y: number;
  fill: string;
  lineWidth: number;
}> = ({ x, y, fill, lineWidth }) => {
  const theme = useTheme();

  return (
    <g className="arrow">
      <polygon
        points={`${x},${y - 1.5 * lineWidth} ${x - 2 * lineWidth},${y + 1.5 * lineWidth} ${x + 2 * lineWidth},${
          y + 1.5 * lineWidth
        }`}
        style={{ fill }}
        stroke={theme.palette.background.paper}
        strokeWidth={2}
      />
      <polygon
        points={`${x - lineWidth / 2},${y - 2 * lineWidth} ${x + lineWidth / 2},${y - 2 * lineWidth} ${
          x + lineWidth / 2
        },${y + 2 * lineWidth} ${x - lineWidth / 2},${y + 2 * lineWidth}`}
        style={{ fill }}
      />
    </g>
  );
};

export default Triangle;
