import { Stack } from '@mui/material';
import JSONViewer from 'lib/components/display/json';
import Markdown from 'lib/components/display/markdown';
import type { ActionResult } from 'lib/types/action';
import type { WithActionData } from 'lib/types/WithActionData';
import type { FC, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { usePluginStore } from 'react-pluggable';
import clueUIPluginStore from '../../../../plugins/store';

const Result: FC<{ result: WithActionData<ActionResult>; [additionalProp: string]: any }> = ({
  result,
  ...additionalProps
}) => {
  const pluginStore = usePluginStore();
  const { t } = useTranslation();

  const plugin = clueUIPluginStore.getPlugin(result.format, 'action', result.actionId);

  if (plugin) {
    const component = pluginStore.executeFunction(`${plugin}.actionResult`, {
      result,
      ...additionalProps
    }) as ReactNode;

    if (component) {
      return component;
    }
  }

  return (
    <Stack sx={{ overflowY: 'auto' }}>
      <Markdown md={t('format.not.recognized', { format: result.format })} />
      <JSONViewer data={result} collapse forceCompact />
    </Stack>
  );
};

export default Result;
