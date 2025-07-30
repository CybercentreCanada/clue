import { TuiSearchColumn } from 'commons/addons/search';
import { ReactNode } from 'react';
import { TuiListItemProps } from '..';

export type TuiTableColumn = TuiSearchColumn & {
  path?: string;
  sortable?: boolean;
  width?: 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12;
};

export type TuiTableRowDetailRenderer<T> = (props: TuiListItemProps<T>) => ReactNode;

export type TuiTableCellRenderer<T> = (
  value: any,
  columnIndex: number,
  column: TuiTableColumn,
  props: TuiListItemProps<T>
) => ReactNode;
