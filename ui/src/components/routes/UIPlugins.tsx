import type { Monaco } from '@monaco-editor/react';
import { Editor, useMonaco } from '@monaco-editor/react';
import { PlayArrow } from '@mui/icons-material';
import {
  Autocomplete,
  Badge,
  Box,
  Button,
  Divider,
  LinearProgress,
  Stack,
  Switch,
  TextField,
  Typography,
  useTheme
} from '@mui/material';

import PageCenter from 'commons/components/pages/PageCenter';
import useThemeBuilder from 'commons/components/utils/hooks/useThemeBuilder';
import useMyTheme from 'components/hooks/useMyTheme';
import Result from 'lib/components/actions/formats';
import Markdown from 'lib/components/display/markdown';
import { FetcherResultView } from 'lib/components/fetchers/FetcherResultView';
import useClueUIPlugins from 'lib/hooks/useClueUIPlugins';
import type { ActionResult, FetcherResult } from 'lib/main';
import type { WithActionData } from 'lib/types/WithActionData';
import isEmpty from 'lodash-es/isEmpty';
import type { editor } from 'monaco-editor';
import type { FC } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { usePluginStore } from 'react-pluggable';

const UIPlugins: FC = () => {
  const { t } = useTranslation();
  const themeBuilder = useThemeBuilder();
  const theme = useTheme();
  const myTheme = useMyTheme();

  const { clueUIPluginStore } = useClueUIPlugins();
  const pluginStore = usePluginStore();

  const monaco = useMonaco();
  const editor = useRef<editor.IStandaloneCodeEditor>(null);

  const [pluginName, setPluginName] = useState('');

  const [format, setFormat] = useState('');
  const [returnedType, setReturnedType] = useState<'action' | 'fetcher'>('action');

  const [rawValue, setRawValue] = useState('');

  const [outputValue, setOutputValue] = useState('');

  const [displayPlugin, setDisplayPlugin] = useState<
    { id: string; format: string; returnedType: 'action' | 'fetcher' } | undefined
  >(undefined);

  const pluginNames = useMemo(() => {
    if (clueUIPluginStore) {
      return clueUIPluginStore.getPlugins(format, returnedType) ?? [];
    }
    return [];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [format, returnedType, clueUIPluginStore, clueUIPluginStore.plugins.length]);

  const availableFormats = useMemo(() => {
    return clueUIPluginStore.getAvailableFormats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clueUIPluginStore, pluginNames, pluginStore]);

  const pluginDisplayName = useMemo(() => {
    if (displayPlugin?.id) {
      const name = pluginStore.executeFunction(`${displayPlugin.id}.getPluginName`) as string;

      if (name) {
        return name;
      }
    }
  }, [displayPlugin, pluginStore]);

  const pluginDocumentationString = useMemo(() => {
    if (displayPlugin?.id) {
      const documentation = pluginStore.executeFunction(`${displayPlugin.id}.documentation`) as string;

      if (documentation) {
        return documentation;
      }
    }
  }, [displayPlugin, pluginStore]);

  const pluginEditorLanguage = useMemo(() => {
    if (pluginName) {
      const language = pluginStore.executeFunction(`${pluginName}.editorLanguage`) as string;

      if (language) {
        return language;
      }
    }
  }, [pluginName, pluginStore]);

  const pluginExampleInput = useMemo(() => {
    if (pluginName) {
      const exampleInput = pluginStore.executeFunction(`${pluginName}.exampleInput`);

      if (exampleInput) {
        return exampleInput;
      }
    }
  }, [pluginName, pluginStore]);

  const pluginValidationErrors = useMemo(() => {
    const errors: string[] = [];
    if (pluginName.length === 0) {
      errors.push(t('route.plugins.validation.select.plugin'));
    }
    if (pluginName.length === 0 || pluginNames.indexOf(pluginName) === -1) {
      errors.push(t('route.plugins.validation.no.plugin.for.format'));
    }
    return errors;
  }, [pluginName, pluginNames, t]);

  const formatValidationErrors = useMemo(() => {
    const errors: string[] = [];
    if (pluginName.length === 0 && pluginNames.indexOf(pluginName) === -1) {
      errors.push(t('route.plugins.validation.no.plugin.for.format'));
    }
    return errors;
  }, [pluginName, pluginNames, t]);

  const validationErrors = useMemo(
    () => [...pluginValidationErrors, ...formatValidationErrors],
    [pluginValidationErrors, formatValidationErrors]
  );

  const validationError = useMemo(
    () => (pluginValidationErrors.length > 0 ? pluginValidationErrors[0] : null),
    [pluginValidationErrors]
  );

  const handlePluginChange = useCallback((pluginValue: string | null) => {
    setPluginName(pluginValue ?? '');
  }, []);

  const handleFormatChange = useCallback((formatValue: string | null) => {
    setFormat(formatValue ?? '');
  }, []);

  useEffect(() => {
    if (pluginExampleInput) {
      setRawValue(pluginExampleInput);
    }
  }, [pluginExampleInput]);

  const submitDisabled = useMemo(() => {
    return isEmpty(pluginNames) || validationErrors.length > 0;
  }, [pluginNames, validationErrors]);

  const handleSubmit = useCallback(() => {
    if (submitDisabled) {
      return;
    }
    setOutputValue(rawValue);
    setDisplayPlugin({ id: pluginName, format, returnedType });
  }, [pluginName, format, rawValue, returnedType, submitDisabled]);

  useEffect(() => {
    if (!editor.current || !monaco) {
      return;
    }

    const executeDisposable = monaco.editor.addEditorAction({
      id: 'execute-plugin',
      label: 'Execute Plugin',
      contextMenuGroupId: 'clue',
      keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter],
      run: handleSubmit
    });

    return () => executeDisposable.dispose();
  }, [handleSubmit, monaco]);

  useEffect(() => {
    if (!monaco) {
      return;
    }

    monaco.editor.setTheme(theme.palette.mode === 'light' ? 'clue' : 'clue-dark');
  }, [monaco, theme.palette.background.paper, theme.palette.mode]);

  const beforeEditorMount = useCallback(
    (_monaco: Monaco) => {
      let lightBackground = themeBuilder.lightTheme.palette.background.paper;
      // monaco doesn't like colours in the form #fff, with only three digits.
      if (lightBackground.startsWith('#') && lightBackground.length < 7) {
        lightBackground = lightBackground.replace(/(\w)/g, '$1$1');
      }

      _monaco.editor.defineTheme('clue', {
        base: 'vs',
        inherit: true,
        rules: [],
        colors: {
          'editor.background': lightBackground
        }
      });

      let darkBackground = myTheme.palette.dark.background.paper;
      // monaco doesn't like colours in the form #fff, with only three digits.
      if (darkBackground.startsWith('#') && darkBackground.length < 7) {
        darkBackground = darkBackground.replace(/(\w)/g, '$1$1');
      }
      _monaco.editor.defineTheme('clue-dark', {
        base: 'vs-dark',
        inherit: true,
        rules: [],
        colors: {
          'editor.background': darkBackground
        }
      });
    },
    [themeBuilder, myTheme]
  );

  const changesMade = useMemo(() => {
    if (!displayPlugin) {
      return false;
    }
    return (
      rawValue !== outputValue ||
      displayPlugin.format !== format ||
      displayPlugin.returnedType !== returnedType ||
      displayPlugin.id !== pluginName
    );
  }, [displayPlugin, rawValue, outputValue, format, returnedType, pluginName]);

  const loadingPlugins = useMemo(() => clueUIPluginStore?.plugins?.length === 0, [clueUIPluginStore?.plugins?.length]);

  return (
    <PageCenter maxWidth="1800px" textAlign="left" height="100%">
      <Box position="absolute" top={50} left={0} right={0} bottom={0} p={2}>
        <Stack gap={1} height="100%">
          <Typography variant="h3" sx={{ flexShrink: 1 }}>
            {t('route.plugins')}
          </Typography>
          <Divider flexItem orientation="horizontal" />

          <Stack direction={'row'} flex={1} gap={2} sx={{ overflow: 'hidden', minHeight: 0 }}>
            <Stack spacing={1} flex={1} overflow={'hidden'} gap={1}>
              <Typography sx={{ pt: 2 }}>{t('route.plugins.description')}</Typography>
              <Divider flexItem orientation="horizontal" />
              <LinearProgress sx={{ visibility: loadingPlugins ? 'visible' : 'hidden' }} />
              <Stack gap={2}>
                <Autocomplete
                  size="small"
                  disabled={loadingPlugins}
                  loading={loadingPlugins}
                  value={pluginName}
                  options={pluginNames}
                  onChange={(_, pluginValue) => handlePluginChange(pluginValue)}
                  renderInput={params => (
                    <TextField
                      {...params}
                      label={t('route.plugins.plugin')}
                      error={!!validationError}
                      helperText={validationError}
                    />
                  )}
                  sx={{ flex: 1 }}
                />

                <Autocomplete
                  size="small"
                  sx={{ flex: 1 }}
                  value={format}
                  disabled={loadingPlugins}
                  loading={loadingPlugins}
                  onChange={(_, formatValue) => handleFormatChange(formatValue)}
                  options={availableFormats}
                  renderInput={props => <TextField {...props} label={t('route.plugins.format')} />}
                />
              </Stack>
              <Stack flexGrow={1} sx={{ overflow: 'hidden', minHeight: 0 }} gap={1}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography>{t('route.plugins.input')}</Typography>
                  <Box flex={1} />
                  <Typography
                    color={returnedType === 'action' ? theme.palette.primary.main : theme.palette.text.secondary}
                  >
                    {t('action')}
                  </Typography>
                  <Switch
                    color="default"
                    disabled={isEmpty(pluginNames)}
                    checked={returnedType === 'fetcher'}
                    onChange={(_, checked) => setReturnedType(checked ? 'fetcher' : 'action')}
                  />
                  <Typography
                    color={returnedType === 'fetcher' ? theme.palette.primary.main : theme.palette.text.secondary}
                  >
                    {t('fetcher')}
                  </Typography>
                </Stack>
                <Box
                  flexGrow={1}
                  position={'relative'}
                  sx={{
                    border: '1px solid',
                    borderColor: theme.palette.divider,
                    borderRadius: 1,
                    p: 1,
                    minHeight: 100,
                    overflow: 'hidden'
                  }}
                >
                  <Editor
                    height="100%"
                    width="100%"
                    language={pluginEditorLanguage}
                    theme={theme.palette.mode === 'light' ? 'clue' : 'clue-dark'}
                    value={rawValue}
                    beforeMount={beforeEditorMount}
                    onMount={_editor => (editor.current = _editor)}
                    onChange={value => setRawValue(value ?? '')}
                  />
                </Box>
                <Box flex={1}>
                  <Button
                    disabled={submitDisabled}
                    startIcon={<PlayArrow />}
                    variant="outlined"
                    color="success"
                    onClick={handleSubmit}
                    sx={{ pr: 3 }}
                  >
                    <Badge
                      sx={{
                        '& .MuiBadge-badge': {
                          right: -10,
                          top: 12
                        }
                      }}
                      color={'warning'}
                      badgeContent={changesMade ? 1 : 0}
                      variant="dot"
                    >
                      {t('route.plugins.submit')}
                    </Badge>
                  </Button>
                </Box>
              </Stack>
            </Stack>
            <Divider flexItem orientation="vertical" sx={{ mx: 4 }} />
            <Stack flex={2} minHeight={0} sx={{ overflow: 'hidden' }}>
              {displayPlugin && pluginDisplayName && (
                <>
                  <Typography variant="h6" sx={{ py: 2 }}>
                    {pluginDisplayName}
                  </Typography>
                  <Divider flexItem />
                  <Markdown md={pluginDocumentationString ?? '_No documentation available for this plugin_'} />
                </>
              )}
              <Box
                flex={1}
                position={'relative'}
                sx={{
                  border: '1px solid',
                  borderColor: theme.palette.divider,
                  borderRadius: 1,
                  p: 1,
                  minHeight: 100,
                  overflow: 'hidden'
                }}
              >
                {displayPlugin &&
                  outputValue &&
                  (displayPlugin.returnedType === 'action' ? (
                    <Result
                      pluginName={displayPlugin.id}
                      height="80%"
                      result={
                        {
                          outcome: 'success',
                          output: outputValue,
                          format: displayPlugin.format
                        } as WithActionData<ActionResult>
                      }
                    />
                  ) : (
                    <FetcherResultView
                      pluginName={displayPlugin.id}
                      height="80%"
                      result={{ data: outputValue, format: displayPlugin.format } as FetcherResult}
                    />
                  ))}
              </Box>
            </Stack>
          </Stack>
        </Stack>
      </Box>
    </PageCenter>
  );
};

export default UIPlugins;
