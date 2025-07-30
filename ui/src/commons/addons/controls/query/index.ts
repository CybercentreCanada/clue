export const LS_KEY_QUERY_APPEND = 'templateui.query.append';
export const LS_KEY_QUERY_GLOBAL = 'templateui.query.global';

export type TuiQueryStoreService<T extends TuiQueryItem = TuiQueryItem> = {
  ready: boolean;
  items: T[];
  onCreate: (name: string, query: string, global?: boolean) => Promise<string>;
  onSave: (item: T) => Promise<string>;
  onDelete: (id: string) => Promise<boolean>;
};

const CHANGE_REASON = ['init', 'input', 'q', 'views', 'clear', 'enter', 'button'] as const;

export type TuiQueryChangeReason = (typeof CHANGE_REASON)[number];

export type TuiQueryState = {
  reason: TuiQueryChangeReason;
  query: string;
  items: { key: string; item: TuiQueryItem }[];
  separator: 'AND' | 'OR';
};

export type TuiQueryItem = {
  id?: string;
  type: 'query' | 'separator';
  name?: string;
  value: string;
};

export const buildQuery = (q: string, state: URLSearchParams, store: TuiQueryStoreService): string => {
  const query = state.get(q) || '';
  const params = Array.from(state.entries());
  const items = params
    .filter(([key]) => key !== q)
    .filter(([key, value]) => key === 'sep' || store.items.some(i => i.id === value))
    .map(([key, value], index, _items) => {
      if (key === 'qid') {
        const sq = store.items.find(i => i.id === value);
        return sq.value;
      } else if (key === 'sep') {
        return index === _items.length - 1 && !query ? null : value;
      }
      return null;
    })
    .filter(v => !!v);

  const joiner = [];
  if (items?.length > 0) {
    joiner.push(`${items.join(' ')}`);
  }

  if (items?.length > 0 && query) {
    joiner.unshift('(');
    joiner.push(') AND ');
  }

  if (query) {
    joiner.push(query);
  }

  return joiner.join('');
};
