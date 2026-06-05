import { Stack } from '@mui/material';
import JSONViewer from 'lib/components/display/json';
import Markdown from 'lib/components/display/markdown';
import type { FetcherResult } from 'lib/main';
import type { FC, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { usePluginStore } from 'react-pluggable';
import clueUIPluginStore from '../../../plugins/store';

export const FetcherResultView: FC<{ result: FetcherResult }> = ({ result }) => {
  const pluginStore = usePluginStore();
  const { t } = useTranslation();

  const availablePlugins = clueUIPluginStore.getPluginsByFormat(result.format);
  if (availablePlugins.length > 0) {
    // return the first available plugin for this format
    const plugin = availablePlugins.at(0);
    if (plugin) {
      const component = pluginStore.executeFunction(`${plugin}.renderFetcherResult`, { result }) as ReactNode;

      if (component) {
        return component;
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
