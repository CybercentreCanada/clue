import { Stack } from '@mui/material';
import JSONViewer from 'lib/components/display/json';
import Markdown from 'lib/components/display/markdown';
import type { RenderFetcherResultProps } from 'lib/plugins/ClueUIPlugin';
import clueUIPluginStore from 'lib/plugins/store';
import type { FC, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { usePluginStore } from 'react-pluggable';
import ErrorBoundary from '../ErrorBoundary';

export const FetcherResultView: FC<RenderFetcherResultProps & { fetcherId?: string }> = ({
  pluginName,
  result,
  fetcherId,
  ...props
}) => {
  const pluginStore = usePluginStore();
  const { t } = useTranslation();

  const availablePlugin =
    pluginName ?? clueUIPluginStore.getPlugin(result.format ?? 'undefined', 'fetcher', undefined, fetcherId);
  if (availablePlugin) {
    // return the first available plugin for this format
    try {
      const component = pluginStore.executeFunction(`${availablePlugin}.fetcherResult`, {
        result,
        fetcherId,
        ...props
      }) as ReactNode;
      if (component !== undefined) {
        return <ErrorBoundary>{component}</ErrorBoundary>;
      }
    } catch {
      return (
        <ErrorBoundary>
          <Stack sx={{ overflowY: 'auto' }}>
            <Markdown md={t('format.render.error', { format: result.format })} />
            <JSONViewer data={result} collapse forceCompact />
          </Stack>
        </ErrorBoundary>
      );
    }
  }

  return (
    <Stack sx={{ overflowY: 'auto' }}>
      <Markdown md={t('format.not.recognized', { format: result.format })} />
      <JSONViewer data={result} collapse forceCompact />
    </Stack>
  );
};
