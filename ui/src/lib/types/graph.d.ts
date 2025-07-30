export type Operator = '=' | '<' | '>' | '!=' | '<=' | '>=' | '~';

export interface BaseComparator {
  field: string;
  operator: Operator;
  value: string | number;
}

export interface ZoomField extends BaseComparator {
  zoom: number;
  label: string;
}

export interface ColorStyler {
  color: string;
}

export interface SizeStyler {
  size: number;
}

export type Stylers = Partial<ColorStyler & SizeStyler>;

export interface NodeStyler extends BaseComparator, Partial<Stylers> {
  type: 'node';
}

export interface EdgeStyler extends Partial<Stylers> {
  type: 'edge';
  source: BaseComparator;
  operator: Operator;
  target: BaseComparator;
}

export interface Metadata<T extends 'nested' | 'node_edge' | 'children'> {
  type: T;
  related?: { [dataset: string]: string };
  display?: {
    visualization?: {
      type: string;
      config?: { [index: string]: any };
    };
    displayField?: ZoomField[];
    styles?: Array<NodeStyler | EdgeStyler>;
  };
  parent?: string;
  summary?: string;
  subgraphs?: BaseComparator[];
}

export type Dataset = NestedDataset | NodeEdgeDataset | ChildrenDataset;

export const isNested = (dataset: Dataset): dataset is NestedDataset => {
  return dataset.metadata.type === 'nested';
};

export interface NestedDataset {
  id: string;
  metadata: Metadata<'nested'>;
  data: RawEntry[][];
}

export const isNodeEdge = (dataset: Dataset): dataset is NestedDataset => {
  return dataset.metadata.type === 'node_edge';
};

interface NodeEdgeDataset {
  id: string;
  metadata: Metadata<'node_edge'>;
  data: {
    nodes: {
      id: string;
      [data: string]: any;
    }[];
    edges: {
      source: string;
      target: string;
    }[];
  };
}

export interface RawEntry {
  id: string;
  edges?: string[];
  markdown?: string;
  icons?: string[];
  [index: string]: any;
}

export interface ChildrenEntry {
  children?: { [id: string]: ChildrenEntry };
}

export interface ChildrenDataset {
  id: string;
  metadata: Metadata<'children'>;
  data: {
    [id: string]: ChildrenEntry;
    raw_data?: any;
  };
}
