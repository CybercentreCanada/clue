import { useTheme } from '@mui/material';
import type { BaseComparator, EdgeStyler, NodeStyler, Operator } from 'lib/types/graph';
import get from 'lodash-es/get';
import isNil from 'lodash-es/isNil';
import type { CSSProperties } from 'react';
import tinycolor from 'tinycolor2';

const useComparator = () => {
  const theme = useTheme();

  const isBaseComparator = (comparator: BaseComparator | NodeStyler | EdgeStyler): comparator is BaseComparator => {
    return !(comparator as any).type;
  };

  const isNodeStyler = (comparator: NodeStyler | EdgeStyler): comparator is NodeStyler => {
    return comparator.type === 'node';
  };

  const runOperator = (value1: any, operator: Operator, value2: any): boolean => {
    if (!operator || !value2) {
      return true;
    }

    let result;
    switch (operator) {
      case '=': {
        // eslint-disable-next-line eqeqeq
        result = (isNil(value1) ? '' : value1).toString() == value2?.toString();
        break;
      }
      case '<': {
        result = parseFloat(value1) < parseFloat(value2);
        break;
      }
      case '>': {
        result = parseFloat(value1) > parseFloat(value2);
        break;
      }
      case '!=': {
        // eslint-disable-next-line eqeqeq
        result = value1?.toString() != value2?.toString();
        break;
      }
      case '<=': {
        result = parseInt(value1) <= parseInt(value2);
        break;
      }
      case '>=': {
        result = parseInt(value1) >= parseInt(value2);
        break;
      }
      case '~': {
        const strValue1 = (value1?.toString?.() ?? '') as string;
        const strValue2 = (value2.toString?.() ?? '') as string;
        result = !!strValue1 && strValue1.toLowerCase().includes(strValue2.toLowerCase());
        break;
      }
      default: {
        result = false;
      }
    }

    // console.log(value1, operator, value2, result);
    return result;
  };

  const runBaseComparator = (comparator: BaseComparator, node: { [index: string]: any }): boolean =>
    runOperator(get(node, comparator.field), comparator.operator, comparator.value);

  const runNodeComparator = (comparator: NodeStyler, node: { [index: string]: any }): CSSProperties => {
    const nodeValue = get(node, comparator.field);

    if (!runOperator(nodeValue, comparator.operator, comparator.value)) {
      return {};
    }

    const styles: CSSProperties = {};

    if (comparator.color) {
      const color: string = theme.palette[comparator.color]?.main ?? comparator.color;

      styles.fill = color;
      try {
        styles.stroke = tinycolor(color).darken(10).toString();
      } catch {
        styles.stroke = color;
      }
    }

    if (comparator.size) {
      styles.strokeWidth = comparator.size;
      styles.fontSize = comparator.size;
    }

    return styles;
  };

  const runEdgeComparator = (
    _comparator: EdgeStyler,
    _source: { [index: string]: any },
    _target: { [index: string]: any }
  ): CSSProperties => {
    return {};
  };

  const runComparator = (
    comparator: BaseComparator | NodeStyler | EdgeStyler,
    nodeOrSource: { [index: string]: any },
    target?: { [index: string]: any }
  ): CSSProperties | boolean => {
    if (isBaseComparator(comparator)) {
      return runBaseComparator(comparator, nodeOrSource);
    }

    if (isNodeStyler(comparator)) {
      return runNodeComparator(comparator, nodeOrSource);
    }

    return runEdgeComparator(comparator, nodeOrSource, target);
  };

  const runComparators = (
    comparators: (NodeStyler | EdgeStyler)[],
    nodeOrSource: { [index: string]: any },
    target?: { [index: string]: any }
  ): CSSProperties => {
    return (comparators ?? [])
      .map(comparator => runComparator(comparator, nodeOrSource, target) as CSSProperties)
      .reduce((acc, val) => ({ ...acc, ...val }), {} as CSSProperties);
  };

  return { runComparators, runComparator };
};

export default useComparator;
