export const buildHorizontalLine = ({
  paddingAtLevel,
  numLines,
  distanceX,
  distanceY,
  childX,
  childY,
  childHeight,
  parentX,
  parentY,
  linePaddingX,
  nodeLocations,
  dest,
  arcRadius
}) => {
  const d: string[] = [];

  const verticalLineX = childX - (paddingAtLevel - numLines) * linePaddingX;

  if (distanceX === 0) {
    if (distanceY === 0) {
      d.push(
        `M ${parentX} ${parentY}`,
        `L ${parentX - linePaddingX + 3} ${parentY}`,
        `A 3 3 90 0 0 ${verticalLineX} ${parentY + 3}`
      );

      d.push(
        `L ${verticalLineX} ${nodeLocations[dest.id][1] - 3}`,
        `A 3 3 90 0 0 ${verticalLineX + 3} ${nodeLocations[dest.id][1]}`,
        `L ${childX} ${nodeLocations[dest.id][1]}`
      );
    } else {
      d.push(`M ${parentX} ${parentY}`, `L ${verticalLineX + arcRadius} ${parentY}`);
      if (Math.sign(distanceY) < 0) {
        d.push(
          `A ${arcRadius} ${arcRadius} 90 0 1 ${verticalLineX} ${parentY - arcRadius}`,
          `L ${verticalLineX} ${childY + arcRadius}`,
          `A ${arcRadius} ${arcRadius} 90 0 1 ${verticalLineX + arcRadius} ${childY}`
        );
      } else {
        d.push(
          `A ${arcRadius} ${arcRadius} 90 0 0 ${verticalLineX} ${parentY + arcRadius}`,
          `L ${verticalLineX} ${childY - arcRadius}`,
          `A ${arcRadius} ${arcRadius} 90 0 0 ${verticalLineX + arcRadius} ${childY}`
        );
      }
      d.push(`L ${childX} ${childY}`);
    }
  } else {
    d.push(`M ${parentX} ${parentY}`);

    if (Math.sign(distanceY) < 0) {
      if (Math.sign(distanceX) < 0) {
        d.push(
          `L ${verticalLineX + arcRadius} ${parentY}`,
          `A ${arcRadius} ${arcRadius} 90 0 1 ${verticalLineX} ${parentY - arcRadius}`
        );
      } else {
        d.push(
          `L ${verticalLineX - arcRadius} ${parentY}`,
          `A ${arcRadius} ${arcRadius} 90 0 0 ${verticalLineX} ${parentY - arcRadius}`
        );
      }

      d.push(
        `L ${verticalLineX} ${childY + childHeight / 2 + arcRadius}`,
        `A ${arcRadius} ${arcRadius} 90 0 1 ${verticalLineX + arcRadius} ${childY + childHeight / 2}`
      );
    } else {
      if (Math.sign(distanceX) < 0) {
        d.push(
          `L ${verticalLineX + arcRadius} ${parentY}`,
          `A ${arcRadius} ${arcRadius} 90 0 0 ${verticalLineX} ${parentY + arcRadius}`
        );
      } else {
        d.push(
          `L ${verticalLineX - arcRadius} ${parentY}`,
          `A ${arcRadius} ${arcRadius} 90 0 1 ${verticalLineX} ${parentY + arcRadius}`
        );
      }

      d.push(
        `L ${verticalLineX} ${childY + childHeight / 2 - arcRadius}`,
        `A ${arcRadius} ${arcRadius} 90 0 0 ${verticalLineX + arcRadius} ${childY + childHeight / 2}`
      );
    }

    d.push(`L ${childX} ${childY + childHeight / 2}`);
  }

  return d;
};

export const buildVerticalLine = ({
  paddingAtLevel,
  numLines,
  distanceX,
  distanceY,
  childX,
  childY,
  childHeight,
  parentX,
  parentY,
  linePaddingX,
  arcRadius
}) => {
  const d: string[] = [];
  const verticalLineX = (Math.sign(distanceY) < 0 ? childX : parentX) - (paddingAtLevel - numLines) * linePaddingX;

  if (distanceX === 0) {
    d.push(`M ${parentX} ${parentY}`, `L ${childX} ${childY}`);
  } else {
    d.push(`M ${parentX} ${parentY}`);

    if (Math.sign(distanceY) < 0) {
      if (Math.sign(distanceX) < 0) {
        d.push(
          `L ${verticalLineX + arcRadius} ${parentY}`,
          `A ${arcRadius} ${arcRadius} 90 0 1 ${verticalLineX} ${parentY - arcRadius}`,
          `L ${verticalLineX} ${childY + childHeight / 2 + arcRadius}`,
          `A ${arcRadius} ${arcRadius} 90 0 1 ${verticalLineX + arcRadius} ${childY + childHeight / 2}`
        );
      } else {
        d.push(
          `L ${verticalLineX - arcRadius} ${parentY}`,
          `A ${arcRadius} ${arcRadius} 90 0 0 ${verticalLineX} ${parentY - arcRadius}`,
          `L ${verticalLineX} ${childY + childHeight / 2 + arcRadius}`,
          `A ${arcRadius} ${arcRadius} 90 0 0 ${verticalLineX - arcRadius} ${childY + childHeight / 2}`
        );
      }
    } else {
      d.push(
        `L ${verticalLineX + arcRadius} ${parentY}`,
        `A ${arcRadius} ${arcRadius} 90 0 0 ${verticalLineX} ${parentY + arcRadius}`,
        `L ${verticalLineX} ${childY + childHeight / 2 - arcRadius}`,
        `A ${arcRadius} ${arcRadius} 90 0 0 ${verticalLineX + arcRadius} ${childY + childHeight / 2}`
      );
    }

    d.push(`L ${childX} ${childY + childHeight / 2}`);
  }

  return d;
};
