import { useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router';
import { useSearchParams } from 'react-router-dom';
import { TuiSearchRequest } from '..';
import TuiSearchModel from '../models/TuiSearchModel';
import { isMatcher, isSeparator, isSorter, TuiSearchOperator, TuiSearchTerm } from '../models/TuiSearchTerms';

const SPLITER = '::';

const FILTER_PARAM = 'filter';

const SORTER_PARAM = 'sorter';

const OFFSET_PARAM = 'offset';

const LIMIT_PARAM = 'limit';

const PARAMETER_NAMES = [OFFSET_PARAM, LIMIT_PARAM, FILTER_PARAM, SORTER_PARAM];

type TuiSearchParamType = (typeof PARAMETER_NAMES)[number];

export default function useTuiSearchParams() {
  const reactNavigate = useNavigate();
  const [params, setParams] = useSearchParams();

  const _serialize = useCallback((t: TuiSearchTerm<any>): string => {
    if (isMatcher(t)) {
      return `${t.column}${SPLITER}${t.operator}${SPLITER}${t.value}`;
    } else if (isSorter(t)) {
      return `${t.column}${SPLITER}${t.value}`;
    } else if (isSeparator(t)) {
      return t.operator;
    }
    return null;
  }, []);

  const _deserialize = useCallback((_params: string[], type: TuiSearchParamType): TuiSearchTerm<any>[] => {
    return _params
      .filter(p => !!p)
      .map(p => {
        const parts = p.split(SPLITER);
        if (type === SORTER_PARAM) {
          return { column: parts[0], operator: 'orderBy', value: parts[1] };
        } else if (isMatcher(parts[1])) {
          return { column: parts[0], operator: parts[1] as TuiSearchOperator, value: parts[2] };
        } else if (isSeparator(parts[0])) {
          return { operator: parts[0] as TuiSearchOperator };
        }
        return null;
      })
      .filter(t => !!t) as TuiSearchTerm<any>[];
  }, []);

  const serialize = useCallback(
    (request: TuiSearchRequest) => {
      const _params = new URLSearchParams(request.parameters);

      request.filters?.forEach(t => {
        _params.append(FILTER_PARAM, _serialize(t));
      });

      request.sorters?.forEach(t => {
        _params.append(SORTER_PARAM, _serialize(t));
      });

      if (request?.offset !== undefined && request.offset !== null) {
        _params.set(OFFSET_PARAM, `${request.offset}`);
      }

      if (request?.limit !== undefined && request.limit !== null) {
        _params.set(LIMIT_PARAM, `${request.limit}`);
      }

      return _params;
    },
    [_serialize]
  );

  const deserialize = useCallback(
    (_params: string | URLSearchParams, model: TuiSearchModel = new TuiSearchModel()) => {
      _params = typeof _params === 'string' ? new URLSearchParams(_params) : _params;
      const entries = Array.from(_params.entries());

      if (entries.length === 0) {
        return model;
      }

      _deserialize(_params.getAll(FILTER_PARAM), FILTER_PARAM).forEach(t => model.filters().insert(t));

      _deserialize(_params.getAll(SORTER_PARAM), SORTER_PARAM).forEach(t => model.sorters().insert(t));

      if (_params.has(OFFSET_PARAM) && _params.get(OFFSET_PARAM) !== undefined && _params.get(OFFSET_PARAM) !== null) {
        model.offset(parseInt(_params.get(OFFSET_PARAM)));
      }

      if (_params.has(LIMIT_PARAM) && !!_params.get(LIMIT_PARAM)) {
        model.limit(parseInt(_params.get(LIMIT_PARAM)));
      }

      entries.filter(e => !PARAMETER_NAMES.some(p => p === e[0])).forEach(p => model.parameters().append(p[0], p[1]));

      return model.rebuild();
    },
    [_deserialize]
  );

  const read = useCallback(
    (model: TuiSearchModel = new TuiSearchModel()) => {
      return deserialize(params, model);
    },
    [params, deserialize]
  );

  const write = useCallback(
    (request: TuiSearchRequest) => {
      setParams(request ? serialize(request) : new URLSearchParams(), { replace: true });
    },
    [setParams, serialize]
  );

  const uri = useCallback(
    (_uri, search: string | TuiSearchRequest) => {
      return `${_uri}?${typeof search === 'string' ? search : serialize(search).toString()}`;
    },
    [serialize]
  );

  const navigate = useCallback(
    (_uri: string, model?: TuiSearchRequest) => {
      reactNavigate(model ? uri(_uri, model) : _uri);
    },
    [reactNavigate, uri]
  );

  const equal = useCallback(
    (request: TuiSearchRequest, equalsWhenEmpty: boolean = false) => {
      const current = params.toString();
      const compare = serialize(request).toString();
      return current === compare || current.length === 0;
    },
    [params, serialize]
  );

  return useMemo(
    () => ({
      serialize,
      deserialize,
      read,
      write,
      uri,
      navigate,
      equal
    }),
    [serialize, deserialize, read, write, uri, navigate, equal]
  );
}
