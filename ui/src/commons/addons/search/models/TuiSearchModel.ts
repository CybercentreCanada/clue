import { TuiSearchRequest } from '..';
import TuiSearchTerms, { isMatcher, isSeparator, isSorter, TuiSearchDirection, TuiSearchTerm } from './TuiSearchTerms';

export default class TuiSearchModel {
  private _offset: number;

  private _limit: number;

  private _filters: TuiSearchTerms;

  private _sorters: TuiSearchTerms;

  private _parameters: URLSearchParams;

  public constructor(limit: number = 25) {
    this._offset = 0;
    this._limit = limit;
    this._filters = new TuiSearchTerms();
    this._sorters = new TuiSearchTerms();
    this._parameters = new URLSearchParams();
  }

  public offset(offset?: number): number {
    if (offset !== undefined) {
      this._offset = offset;
    }
    return this._offset;
  }

  public limit(limit?: number): number {
    if (limit !== undefined) {
      this._limit = limit;
    }
    return this._limit;
  }

  public filters(): TuiSearchTerms {
    return this._filters;
  }

  public sorters(): TuiSearchTerms {
    return this._sorters;
  }

  public parameters(): URLSearchParams {
    return this._parameters;
  }

  public hasOffset() {
    return this._offset !== undefined && this._offset !== null;
  }

  public withOffset(offset: number): TuiSearchModel {
    this._offset = offset;
    return this.rebuild();
  }

  public hasLimit() {
    return this._limit !== undefined && this._limit !== null;
  }

  public withLimit(limit: number): TuiSearchModel {
    this._limit = limit;
    return this.rebuild();
  }

  public withFilters(terms: TuiSearchTerms): TuiSearchModel {
    this._filters = terms;
    return this.rebuild();
  }

  public withSorters(terms: TuiSearchTerms): TuiSearchModel {
    this._sorters = terms;
    return this.rebuild();
  }

  public withParameters(parameters: URLSearchParams): TuiSearchModel {
    this._parameters = parameters;
    return this.rebuild();
  }

  public filtersOn(column: string): boolean {
    return this.filters()
      .terms()
      .some(t => t.column === column);
  }

  public filtersBy(column: string): TuiSearchTerm<any>[] {
    return this.filters()
      .terms()
      .filter(t => t.column === column && isMatcher(t));
  }

  public sortsOn(column: string): boolean {
    return this.sorters()
      .terms()
      .some(t => t.column === column);
  }

  public sortersBy(column: string): TuiSearchTerm<TuiSearchDirection>[] {
    return this.sorters()
      .terms()
      .filter(t => t.column === column && isSorter(t));
  }

  public reset(): TuiSearchModel {
    const model = new TuiSearchModel(this._limit);
    model._filters = this.filters().reset();
    model._sorters = this.sorters().reset();
    model._parameters = new URLSearchParams();
    model._offset = 0;
    return model;
  }

  public rebuild(): TuiSearchModel {
    const model = new TuiSearchModel(this._limit);
    model._filters = this._filters.rebuild();
    model._sorters = this._sorters.rebuild();
    model._parameters = this._parameters;
    model._offset = this._offset;
    return model;
  }

  public valid(): boolean {
    const even = this._filters.terms().filter((t, i) => i % 2 === 0);
    const odd = this._filters.terms().filter((t, i) => i % 2 === 1);
    return (
      even.every(m => isMatcher(m)) && odd.every(s => isSeparator(s)) && this._sorters.terms().every(o => isSorter(o))
    );
  }

  public request(): TuiSearchRequest {
    return {
      filters: this._filters.terms().filter(t => isSeparator(t) || (t.value !== null && t.value !== undefined)),
      sorters: this._sorters.terms().filter(t => t.value !== null && t.value !== undefined),
      parameters: this._parameters ? Array.from(this._parameters.entries()).map(e => [e[0], e[1]]) : [],
      offset: this._offset,
      limit: this._limit
    };
  }

  public static build({ offset, limit, filters, sorters, parameters }: TuiSearchRequest): TuiSearchModel {
    const model = new TuiSearchModel(limit);
    model._offset = offset || 0;
    model._filters = new TuiSearchTerms('*', filters);
    model._sorters = new TuiSearchTerms('*', sorters);
    parameters?.forEach(p => model._parameters.append(p[0], p[1]));
    return model;
  }
}
