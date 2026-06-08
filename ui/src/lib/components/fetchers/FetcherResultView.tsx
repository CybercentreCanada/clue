import { Stack } from '@mui/material';
import JSONViewer from 'lib/components/display/json';
import Markdown from 'lib/components/display/markdown';
import type { FC, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { usePluginStore } from 'react-pluggable';
import type { RenderFetcherResultProps } from '../../../plugins/ClueUIPlugin';
import clueUIPluginStore from '../../../plugins/store';
import ErrorBoundary from '../ErrorBoundary';

export const FetcherResultView: FC<RenderFetcherResultProps> = ({ result, ...props }) => {
  const pluginStore = usePluginStore();
  const { t } = useTranslation();

  const availablePlugins = clueUIPluginStore.getPlugin(result.format, 'fetcher');
  if (availablePlugins.length > 0) {
    // return the first available plugin for this format
    const plugin = availablePlugins.at(0);
    if (plugin) {
      const component = pluginStore.executeFunction(`${plugin}.fetcherResult`, { result, ...props }) as ReactNode;

      if (component) {
        return <ErrorBoundary>{component}</ErrorBoundary>;
      }
    }
  }

  return (
    <Stack sx={{ overflowY: 'auto' }}>
      <Markdown md={t('format.not.recognized', { format: result.format })} />
      <JSONViewer data={result} collapse forceCompact />
    </Stack>
  );
};
