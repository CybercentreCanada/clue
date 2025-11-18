import { v4 as uuid } from 'uuid';

export const MATCHERS = ['like', 'in', 'is', '>=', '<=', '='] as const;

export const SEPARATORS = ['or', 'and'] as const;

export const FILTERS = [...MATCHERS, ...SEPARATORS] as const;

export const SORTERS = ['orderBy'] as const;

export const DIRECTIONS = ['asc', 'desc', 'unset'] as const;

export type TuiSearchMatcher = (typeof MATCHERS)[number];

export type TuiSearchSeparator = (typeof SEPARATORS)[number];

export type TuiSearchOrder = (typeof SORTERS)[number];

export type TuiSearchDirection = (typeof DIRECTIONS)[number];

export type TuiSearchFilter = (typeof FILTERS)[number];

export type TuiSearchOperator = TuiSearchMatcher | TuiSearchSeparator | TuiSearchOrder;

export function isSeparator(term: string | TuiSearchTerm<any>): boolean {
  if (!term) {
    return false;
  }
  const operator = typeof term === 'string' ? term : (term as TuiSearchTerm<any>).operator;
  return term && SEPARATORS.some(m => m === operator);
}

export function isMatcher(term: string | TuiSearchTerm<any>): boolean {
  if (!term) {
    return false;
  }
  const operator = typeof term === 'string' ? term : (term as TuiSearchTerm<any>).operator;
  return term && MATCHERS.some(m => m === operator);
}

export function isSorter(term: string | TuiSearchTerm<any>): boolean {
  if (!term) {
    return false;
  }
  const operator = typeof term === 'string' ? term : (term as TuiSearchTerm<any>).operator;
  return term && SORTERS.some(m => m === operator);
}

export type TuiSearchTerm<T> = {
  id?: string;
  column?: string;
  operator: TuiSearchOperator;
  value?: T;
};

export default class TuiSearchTerms {
  private _cursor: number;

  private _column: string;

  private _placeholder: TuiSearchTerm<any>;

  private _defaultSeparator: TuiSearchSeparator;

  private _separator: TuiSearchSeparator;

  private _defaultMatcher: TuiSearchMatcher;

  private _matcher: TuiSearchMatcher;

  private _terms: TuiSearchTerm<any>[] = [];

  public constructor(
    column: string = '*',
    terms: TuiSearchTerm<any>[] = [],
    separator: TuiSearchSeparator = 'and',
    matcher: TuiSearchMatcher = 'like'
  ) {
    this._cursor = -1;
    this._column = column;
    this._defaultSeparator = separator;
    this._separator = separator;
    this._defaultMatcher = matcher;
    this._matcher = matcher;
    this.withPlaceholder();
    this.load(terms);
    this.insert = this.insert.bind(this);
  }

  private init(term: TuiSearchTerm<any>): TuiSearchTerm<any> {
    if (!term.id) {
      term.id = uuid();
    }
    return term;
  }

  private load(terms: TuiSearchTerm<any>[]): TuiSearchTerms {
    terms.forEach(t => this.insert(t));
    return this;
  }

  public withPlaceholder(column?: string): TuiSearchTerms {
    this._placeholder = column
      ? { column, operator: this._matcher, value: '' }
      : { column: this._column, operator: this._matcher, value: '' };
    return this;
  }

  public withoutPlaceholder(): TuiSearchTerms {
    this._placeholder = null;
    return this;
  }

  public withSeparator(separator: TuiSearchSeparator): TuiSearchTerms {
    this._separator = separator;
    return this;
  }

  public withMatcher(matcher: TuiSearchMatcher): TuiSearchTerms {
    if (this._placeholder) {
      this._placeholder.operator = matcher;
    }
    if (this.get()) {
      this.get().operator = matcher;
    }
    this._matcher = matcher;
    return this;
  }

  public write(value: any): TuiSearchTerms {
    if (this._placeholder && !!value) {
      this._placeholder.value = value;
      this.insert(this._placeholder, true);
    } else {
      this.get().value = value;
    }
    return this;
  }

  public insert(term: TuiSearchTerm<any>, withSeparator: boolean = false): TuiSearchTerms {
    this._cursor = this._cursor + 1;

    if (withSeparator && this.count() > 0) {
      this.insert({ operator: this._separator });
    }

    this._terms.splice(this._cursor, 0, this.init(term));

    if (this.count() > 0) {
      this._placeholder = null;
    }

    if (isMatcher(term)) {
      this._matcher = term.operator as TuiSearchMatcher;
    }

    return this;
  }

  public delete(): TuiSearchTerms {
    return this.remove(this.get());
  }

  public remove(term: TuiSearchTerm<any>): TuiSearchTerms {
    // Find out the position of the term.
    let position = this._terms.findIndex(t => t.id === term.id);

    // Does it exist?
    if (position > -1) {
      // Remove the term.
      const _removed = this._terms.splice(position, 1)[0];

      // If there is nothing remaining,
      //  initialize a new placeholder.
      const _count = this.count();
      if (_count === 0) {
        this._cursor = -1;
        this.withPlaceholder(_removed.column);
      }

      // If we've removed the last element,
      //  decrement the cursor by one.
      else if (_count > 0 && position > _count - 1) {
        position -= 1;
      }

      // Remove trailing separator.
      if (_count > 0 && isSeparator(this._terms[position])) {
        this._terms.splice(position, 1);
      }
    }

    // Ensure cursor is stil within range.
    if (this._cursor > this._terms.length - 1) {
      this._cursor = this._terms.length - 1;
    }

    return this;
  }

  public removeColumn(column: string): TuiSearchTerms {
    this._terms
      .filter(t => t.column === column)
      .forEach(t => {
        this.remove(t);
      });
    return this;
  }

  public move(term: TuiSearchTerm<any>): TuiSearchTerms {
    const index = this._terms.findIndex(t => t === term);
    if (index > -1) {
      this._cursor = index;
      this._placeholder = null;
    } else {
      this.insert(term);
    }
    return this;
  }

  public findById(id: string): TuiSearchTerm<any> {
    return this._terms.find(t => t.id === id);
  }

  public findByColumn(column: string): TuiSearchTerm<any> {
    return this._terms.find(t => t.column === column);
  }

  public findIndexByColumn(column: string): number {
    return this._terms.findIndex(t => t.column === column);
  }

  public has(term: TuiSearchTerm<any>): boolean {
    return this._terms.some(t => t === term);
  }

  public hasColumn(column: string): boolean {
    return this._terms.some(t => t.column === column);
  }

  public get(index?: number): TuiSearchTerm<any> {
    if (index !== undefined) {
      return this._terms[index];
    }
    return this._placeholder || this._terms[this._cursor];
  }

  public separator(): TuiSearchSeparator {
    return this._separator;
  }

  public matcher(): TuiSearchMatcher {
    return this._matcher;
  }

  public matchers(): TuiSearchTerm<any>[] {
    return this._terms ? this._terms.filter(t => isMatcher(t)) : [];
  }

  public sorters(): TuiSearchTerm<any>[] {
    return this._terms ? this._terms.filter(t => isSorter(t)) : [];
  }

  public count(type: string = null): number {
    return this._terms ? this._terms.length : 0;
  }

  public countMatchers(type: string = null): number {
    return this.matchers().length;
  }

  public countSorters(type: string = null): number {
    return this.sorters().length;
  }

  public empty(): boolean {
    return this.count() === 0;
  }

  public terms(): TuiSearchTerm<any>[] {
    return this._terms;
  }

  public isOn(term: TuiSearchTerm<any>): boolean {
    return term === this.get();
  }

  public like(column: string, value: string, withSeparator: boolean = false): TuiSearchTerms {
    this.insert(this.init({ column, operator: 'like', value }), withSeparator);
    return this;
  }

  public eq(column: string, value: any, withSeparator: boolean = false): TuiSearchTerms {
    this.insert(this.init({ column, operator: '=', value }), withSeparator);
    return this;
  }

  public in(column: string, value: string[], withSeparator: boolean = false): TuiSearchTerms {
    this.insert(this.init({ column, operator: 'in', value }), withSeparator);
    return this;
  }

  public gte(column: string, value: string[], withSeparator: boolean = false): TuiSearchTerms {
    this.insert(this.init({ column, operator: '>=', value }), withSeparator);
    return this;
  }

  public ste(column: string, value: string[], withSeparator: boolean = false): TuiSearchTerms {
    this.insert(this.init({ column, operator: '<=', value }), withSeparator);
    return this;
  }

  public or(): TuiSearchTerms {
    this.insert(this.init({ operator: 'or' }));
    return this;
  }

  public and(): TuiSearchTerms {
    this.insert(this.init({ operator: 'and' }));
    return this;
  }

  public orderBy(column: string, value: TuiSearchDirection): TuiSearchTerms {
    this.insert(this.init({ column, operator: 'orderBy', value }));
    return this;
  }

  public reset(): TuiSearchTerms {
    this._cursor = -1;
    this._placeholder = { column: this._column, operator: 'like', value: '' };
    this._separator = this._defaultSeparator;
    this._matcher = this._defaultMatcher;
    this._terms = [];
    return this;
  }

  public rebuild(): TuiSearchTerms {
    const terms = new TuiSearchTerms(
      this._column,
      this._terms.map(t => ({ ...t })),
      this._defaultSeparator
    );
    terms._placeholder = this._placeholder;
    terms._cursor = this._cursor;
    terms._separator = this._separator;
    terms._matcher = this._matcher;
    return terms;
  }
}
