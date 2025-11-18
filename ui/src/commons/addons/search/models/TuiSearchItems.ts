import get from 'lodash-es/get';
import isArray from 'lodash-es/isArray';
import isBoolean from 'lodash-es/isBoolean';
import isNumber from 'lodash-es/isNumber';
import isObject from 'lodash-es/isObject';
import isString from 'lodash-es/isString';
import TuiSearchModel from './TuiSearchModel';
import TuiSearchTerms, { TuiSearchDirection, TuiSearchTerm, isMatcher, isSeparator } from './TuiSearchTerms';

export type TuiSearchItemsResult<T> = {
  limit: number;
  offset: number;
  total: number;
  items: T[];
};

export default class TuiSearchItems<T> {
  private _items: T[] = [];

  private _result: T[] = [];

  private _limit: number;

  private _offset: number = 0;

  public constructor(items: T[] = []) {
    this.load(items);
  }

  private extractValue(item: T, column: string) {
    if (column === '*') {
      return item;
    }
    const _value = get(item, column, '');
    return _value !== undefined ? _value : '';
  }

  private isString(value: any): boolean {
    return isString(value);
  }

  private isNumber(value: any): boolean {
    return isNumber(value);
  }

  private isBoolean(value: any): boolean {
    return isBoolean(value);
  }

  private isArray(value: any): boolean {
    return isArray(value);
  }

  private isObject(value: any): boolean {
    return isObject(value);
  }

  private stringify(value: any): { value: string; stringified: boolean } {
    if (value === undefined || value === null || value === '') {
      return { value: '', stringified: true };
    } else if (this.isString(value)) {
      return { value: value.trim().toLowerCase(), stringified: true };
    } else if (this.isNumber(value) || this.isBoolean(value)) {
      return { value: value.toString(), stringified: true };
    }
    return { value, stringified: false };
  }

  private filter(value: any, term: TuiSearchTerm<any>): boolean {
    const targetValue = this.stringify(value);
    if (targetValue.stringified) {
      if (term.operator === 'like') {
        const termValue = term.value as string;
        return targetValue.value.indexOf(termValue.toLowerCase()) > -1;
      } else if (term.operator === '=') {
        return targetValue.value === `${term.value}`.toLocaleLowerCase();
      } else if (term.operator === 'in') {
        const termValue = term.value as any[];
        return termValue.some(tv => tv === targetValue.value);
      }
    } else if (this.isArray(value)) {
      return value.some((tv: any) => this.filter(tv, term));
    } else if (this.isObject(value)) {
      return Object.values(value).some((ov: any) => this.filter(ov, term));
    }
    return false;
  }

  private evalFilters(filters: TuiSearchTerms) {
    this._result = !filters.empty()
      ? this._items.filter(item => {
          const termValues = filters
            .terms()
            .map(t => {
              if (isMatcher(t)) {
                return this.filter(this.extractValue(item, t.column), t);
              } else if (isSeparator(t)) {
                return t.operator === 'or' ? '||' : '&&';
              } else {
                return null;
              }
            })
            .filter(tv => tv !== null);

          // https://esbuild.github.io/content-types/#direct-eval
          return (0, eval)(termValues.join(' '));
        })
      : this._items;
  }

  private sort(i1: T, i2: T, term: TuiSearchTerm<TuiSearchDirection>): number {
    let result = 0;
    if (term.value === 'unset') {
      return result;
    }
    if (!term.value) {
      term.value = 'asc';
    }
    const v1 = this.extractValue(i1, term.column);
    const v2 = this.extractValue(i2, term.column);
    if (this.isString(v1) && this.isString(v2)) {
      const _v1 = v1 as string;
      const _v2 = v2 as string;
      result = _v1.localeCompare(_v2);
    } else if (this.isNumber(v1) && this.isNumber(v2)) {
      const _v1 = v1 as number;
      const _v2 = v2 as number;
      result = _v1 - _v2;
    } else {
      result = v1.toString().localeCompare(v2.toString());
    }
    return term.value === 'asc' ? result : -result;
  }

  private evalSorters(sorters: TuiSearchTerms) {
    this._result = this._result.concat().sort((i1, i2) => {
      let result = 0;
      for (const term of sorters.terms()) {
        result = this.sort(i1, i2, term);
        if (result !== 0) {
          break;
        }
      }
      return result;
    });
  }

  public reset(): TuiSearchItems<T> {
    this._result = this._items;
    return this;
  }

  public load(items: T[]): TuiSearchItems<T> {
    this._items = items;
    this._result = items;
    return this;
  }

  public apply(model: TuiSearchModel): TuiSearchItems<T> {
    this.evalFilters(model.filters());
    this.evalSorters(model.sorters());
    if (model.offset() !== null) {
      this._offset = model.offset();
    }
    if (model.limit() !== null) {
      this._limit = model.limit();
    }
    return this;
  }

  public search(...values: string[]): TuiSearchItems<T> {
    const model = new TuiSearchModel();
    model.filters().withSeparator('or');
    values.forEach((v, i) => {
      model.filters().like('*', v, true);
    });
    return this.apply(model);
  }

  public limit(limit: number): TuiSearchItems<T> {
    this._limit = limit;
    return this;
  }

  public offset(offset: number): TuiSearchItems<T> {
    this._offset = offset;
    return this;
  }

  public result(): TuiSearchItemsResult<T> {
    let _result = this._result;

    if (this._offset) {
      _result = _result.slice(this._offset);
    }
    if (this._limit) {
      _result = _result.slice(0, this._limit);
    }

    return {
      limit: this._limit,
      offset: this._offset,
      total: this._result.length,
      items: _result
    };
  }
}
