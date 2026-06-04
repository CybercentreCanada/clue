import { Stack } from '@mui/material';
import JSONViewer from 'lib/components/display/json';
import Markdown from 'lib/components/display/markdown';
import type { ActionResult } from 'lib/types/action';
import type { WithActionData } from 'lib/types/WithActionData';
import type { FC, ReactNode } from 'react';
import { usePluginStore } from 'react-pluggable';
import clueUIPluginStore from '../../../../plugins/store';
import FileResult from './FileResult';

const Result: FC<{ result: WithActionData<ActionResult> }> = ({ result }) => {
  const pluginStore = usePluginStore();

  let availablePlugins = clueUIPluginStore.getPluginsByActionId(result.actionId);
  if (availablePlugins.length > 0) {
    // return the first available plugin for this actionId
    const plugin = availablePlugins.at(0);
    if (plugin) {
      const component = pluginStore.executeFunction(`${plugin}.render`, { result }) as ReactNode;

      if (component) {
        return component;
      }
    }
  }

  availablePlugins = clueUIPluginStore.getPluginsByFormat(result.format);
  if (availablePlugins.length > 0) {
    // return the first available plugin for this format
    const plugin = availablePlugins.at(0);
    if (plugin) {
      const component = pluginStore.executeFunction(`${plugin}.render`, { result }) as ReactNode;

      if (component) {
        return component;
      }
    }
  }

  if (result.format === 'markdown') {
    return <Markdown md={result.output} />;
  }

  if (result.format === 'json') {
    return <JSONViewer data={result.output} collapse forceCompact />;
  }

  if (result.format === 'file') {
    return <FileResult result={result} />;
  }

  return (
    <Stack sx={{ overflowY: 'auto' }}>
      <Markdown md={'`' + result.format + '` is not recognized as a format in this application.'} />
      <JSONViewer data={result} collapse forceCompact />
    </Stack>
  );
};

export default Result;
