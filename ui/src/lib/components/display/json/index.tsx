import type { CollapsedFieldProps, ReactJsonViewProps } from '@microlink/react-json-view';
import type { StackProps } from '@mui/material';
import { Skeleton, Stack, useTheme } from '@mui/material';
import { TuiPhrase } from 'commons/addons/controls';
import { flatten } from 'flat';
import { ClueComponentContext } from 'lib/hooks/ClueComponentContext';
import { useMyLocalStorageItem } from 'lib/hooks/useMyLocalStorage';
import { StorageKey } from 'lib/utils/constants';
import { removeEmpty, searchObject } from 'lib/utils/utils';
import type { ComponentType, FC } from 'react';
import { lazy, useEffect, useMemo, useState } from 'react';
import { useContextSelector } from 'use-context-selector';

const JSONViewer: FC<{
  data: object;
  collapse?: boolean;
  forceCompact?: boolean;
  slotProps?: {
    stack?: StackProps;
    json?: Partial<ReactJsonViewProps>;
  };
}> = ({ data, collapse = true, forceCompact = false, slotProps }) => {
  const theme = useTheme();

  const [compact] = useMyLocalStorageItem<boolean>(StorageKey.COMPACT_JSON);
  const [flat] = useMyLocalStorageItem<boolean>(StorageKey.FLATTEN_JSON);
  const _ProvidedReactJson = useContextSelector(ClueComponentContext, ctx => ctx?.ReactJson);
  const { t } = useContextSelector(ClueComponentContext, ctx => ctx?.i18next);

  const [ReactJson, setReactJson] = useState<ComponentType<ReactJsonViewProps>>(null);
  const [query, setQuery] = useState('');

  const isDark = useMemo(() => theme.palette.mode === 'dark', [theme]);
  const filteredData = useMemo(() => removeEmpty(data, compact || forceCompact), [compact, data, forceCompact]);

  const searchedData = useMemo(() => {
    const _searchedData = searchObject(filteredData, query);

    return flat ? flatten(_searchedData) : _searchedData;
  }, [filteredData, flat, query]);

  const hasError = useMemo(() => {
    try {
      new RegExp(query);

      return false;
    } catch {
      return true;
    }
  }, [query]);

  useEffect(() => {
    if (_ProvidedReactJson) {
      setReactJson(() => _ProvidedReactJson);
    } else {
      setReactJson(lazy(() => import('@microlink/react-json-view')));
    }
  }, [_ProvidedReactJson]);

  const shouldCollapse = (field: CollapsedFieldProps) => {
    return (field.name !== 'root' && field.type !== 'object') || field.namespace.length > 3;
  };

  return data ? (
    <Stack
      direction="column"
      spacing={1}
      {...slotProps?.stack}
      sx={{
        '& > div:first-of-type': { mt: 1, mr: 0.5 },
        ...(Array.isArray(slotProps?.stack?.sx) ? slotProps?.stack?.sx : [slotProps?.stack?.sx])
      }}
    >
      <TuiPhrase
        value={query}
        onChange={setQuery}
        size="small"
        error={hasError}
        label={t('json.viewer.search.label')}
        placeholder={t('json.viewer.search.prompt')}
      />
      {ReactJson && (
        <ReactJson
          src={searchedData}
          theme={isDark ? 'summerfruit' : 'summerfruit:inverted'}
          indentWidth={2}
          displayDataTypes={!compact && !forceCompact}
          displayObjectSize={!compact && !forceCompact}
          shouldCollapse={collapse ? shouldCollapse : false}
          quotesOnKeys={false}
          style={{
            flex: 1,
            overflow: 'auto',
            height: '100%',
            fontSize: compact || forceCompact ? 'small' : 'smaller',
            borderRadius: theme.shape.borderRadius,
            padding: theme.spacing(1)
          }}
          enableClipboard={_data => {
            if (typeof _data.src === 'string') {
              navigator.clipboard.writeText(_data.src);
            } else {
              navigator.clipboard.writeText(JSON.stringify(_data.src));
            }
          }}
          {...({
            // Type declaration is wrong - this is a valid prop
            displayArrayKey: !compact && !forceCompact
          } as any)}
          {...slotProps?.json}
        />
      )}
    </Stack>
  ) : (
    <Skeleton width="100%" height="95%" variant="rounded" />
  );
};

export default JSONViewer;
