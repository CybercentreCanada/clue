import countBy from 'lodash-es/countBy';
import entries from 'lodash-es/entries';
import filter from 'lodash-es/filter';
import groupBy from 'lodash-es/groupBy';
import map from 'lodash-es/map';
import mapValues from 'lodash-es/mapValues';
import maxBy from 'lodash-es/maxBy';
import orderBy from 'lodash-es/orderBy';
import reverse from 'lodash-es/reverse';
import sortBy from 'lodash-es/sortBy';
import toPairs from 'lodash-es/toPairs';

// just add here the lodash functions you want to support
const chainableFunctions = {
  map,
  filter,
  toPairs,
  orderBy,
  groupBy,
  sortBy,
  countBy,
  entries,
  maxBy,
  reverse
};

const chain = <T>(input: T) => {
  let value: any = input;
  const wrapper = {
    ...mapValues(chainableFunctions, (f: any) => (...args: any[]) => {
      // lodash always puts input as the first argument
      value = f(value, ...args);
      return wrapper;
    }),
    value: () => value
  };
  return wrapper;
};

export default chain;
