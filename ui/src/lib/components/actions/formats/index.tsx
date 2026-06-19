import { Stack } from '@mui/material';
import JSONViewer from 'lib/components/display/json';
import Markdown from 'lib/components/display/markdown';
import ErrorBoundary from 'lib/components/ErrorBoundary';
import clueUIPluginStore from 'lib/plugins/store';
import type { ActionResult } from 'lib/types/action';
import type { WithActionData } from 'lib/types/WithActionData';
import { type FC, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { usePluginStore } from 'react-pluggable';

const Result: FC<{ pluginName?: string; result: WithActionData<ActionResult>; [additionalProp: string]: any }> = ({
  pluginName,
  result,
  ...additionalProps
}) => {
  const pluginStore = usePluginStore();
  const { t } = useTranslation();

  const plugin = pluginName ?? clueUIPluginStore.getPlugin(result.format ?? 'undefined', 'action', result.actionId);

  if (plugin) {
    try {
      const component = pluginStore.executeFunction(`${plugin}.actionResult`, {
        result,
        ...additionalProps
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
    <ErrorBoundary>
      <Stack sx={{ overflowY: 'auto' }}>
        <Markdown md={t('format.not.recognized', { format: result.format })} />
        <JSONViewer data={result} collapse forceCompact />
      </Stack>
    </ErrorBoundary>
  );
};

export default Result;
