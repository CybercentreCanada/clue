import { ArrowDownward, ArrowUpward, Remove } from '@mui/icons-material';
import { Badge } from '@mui/material';
import TuiSearchModel from './models/TuiSearchModel';
import { TuiSearchDirection, TuiSearchMatcher, TuiSearchTerm } from './models/TuiSearchTerms';

// Global Search column definition.
export const GLOBAL_COLUMN: TuiSearchColumn = { column: '*', label: 'Global', operators: ['like'] };

// Search Favourite Provider specification.
export type TuiSearchFavouriteProvider = {
  options: TuiSearchFavouriteOption[];
  onSave: (inputValue: string, model: TuiSearchModel) => Promise<boolean>;
  onDelete: (model: TuiSearchFavouriteOption) => Promise<boolean>;
};

// Definition of a search favourite option.
export type TuiSearchFavouriteOption = { id?: string | number; name: string; search: string };

// Definition of a search favourite.
export type TuiSearchFavourite = TuiSearchRequest & {
  name: string;
};

// Definition of a search request.
export type TuiSearchRequest = {
  offset?: number;
  limit?: number;
  filters?: TuiSearchTerm<any>[];
  sorters?: TuiSearchTerm<TuiSearchDirection>[];
  parameters?: [string, any][];
};

// Definition of a search column.
export type TuiSearchColumn = {
  column: string;
  label?: string;
  i18nKey?: string;
  operators?: TuiSearchMatcher[];
};

// Get the correct icon based on the current sorter state.
export const nextSortState = (state: TuiSearchDirection, defaultState?: TuiSearchDirection) => {
  if (state === 'unset') {
    return 'asc';
  }
  if (state === 'asc') {
    return 'desc';
  }
  if (state === 'desc') {
    return 'unset';
  }
  return defaultState || 'asc';
};

// Get the next sort state for the specified state.
export const sortIcon = (sortState: TuiSearchDirection, index: number = -1): React.ReactElement => {
  const icon =
    sortState === 'asc' ? (
      <ArrowDownward fontSize="small" />
    ) : sortState === 'desc' ? (
      <ArrowUpward fontSize="small" />
    ) : (
      <Remove fontSize="small" />
    );
  return index > -1 ? <Badge badgeContent={index + 1}>{icon}</Badge> : icon;
};
