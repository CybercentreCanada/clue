import type { Monaco } from '@monaco-editor/react';
import { Editor, useMonaco } from '@monaco-editor/react';
import { Card, useTheme } from '@mui/material';
import useThemeBuilder from 'commons/components/utils/hooks/useThemeBuilder';
import useMyTheme from 'components/hooks/useMyTheme';
import useClue from 'lib/hooks/useClue';
import type { editor } from 'monaco-editor';
import type { FC } from 'react';
import { memo, useCallback, useEffect, useMemo, useRef } from 'react';

interface QueryEditorProps {
  query: string;
  setQuery: (query: string) => void;
  onSubmit: () => void;
  language?: 'lucene' | 'eql' | 'yaml';
  height?: string;
  width?: string;
  loading?: boolean;
}

const QueryInput: FC<QueryEditorProps> = ({
  query,
  setQuery,
  onSubmit,
  height = '100%',
  width = '100%',
  loading = false
}) => {
  const themeBuilder = useThemeBuilder();
  const theme = useTheme();
  const myTheme = useMyTheme();
  const monaco = useMonaco();
  const { typesDetection, guessType } = useClue();

  const editor = useRef<editor.IStandaloneCodeEditor>(null);
  const collection = useRef<editor.IEditorDecorationsCollection>(null);

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
        rules: [
          {
            token: 'operator',
            foreground: themeBuilder.lightTheme.palette.warning.light.toUpperCase().replaceAll('#', '')
          },
          {
            token: 'string.invalid',
            foreground: themeBuilder.lightTheme.palette.error.main.toUpperCase().replaceAll('#', '')
          },
          {
            token: 'invalid',
            foreground: themeBuilder.lightTheme.palette.error.main.toUpperCase().replaceAll('#', '')
          },
          {
            token: 'boolean',
            foreground: themeBuilder.lightTheme.palette.success.main.toUpperCase().replaceAll('#', '')
          }
        ],
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
        rules: [
          {
            token: 'operator',
            foreground: themeBuilder.darkTheme.palette.warning.light.toUpperCase().replaceAll('#', '')
          },
          {
            token: 'string.invalid',
            foreground: themeBuilder.darkTheme.palette.error.main.toUpperCase().replaceAll('#', '')
          },
          {
            token: 'invalid',
            foreground: themeBuilder.darkTheme.palette.error.main.toUpperCase().replaceAll('#', '')
          },
          {
            token: 'boolean',
            foreground: themeBuilder.darkTheme.palette.success.main.toUpperCase().replaceAll('#', '')
          }
        ],
        colors: {
          'editor.background': darkBackground
        }
      });

      _monaco.languages.register({ id: 'lucene' });
      _monaco.languages.register({ id: 'eql' });
    },
    [themeBuilder, myTheme]
  );

  useEffect(() => {
    if (!editor.current) {
      return;
    }

    const executeDisposable = monaco.editor.addEditorAction({
      id: 'execute-query',
      label: 'Execute Query',
      contextMenuGroupId: 'clue',
      keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter],
      run: () => onSubmit()
    });

    editor.current.getModel().setEOL(monaco.editor.EndOfLineSequence.LF);

    return () => executeDisposable.dispose();
  }, [monaco, onSubmit]);

  useEffect(() => {
    if (!monaco) {
      return;
    }

    monaco.editor.setTheme(theme.palette.mode === 'light' ? 'clue' : 'clue-dark');
  }, [monaco, theme.palette.background.paper, theme.palette.mode]);

  const calculateAnnotations = useCallback(
    (value: string) => {
      if (!editor.current || !monaco) {
        return;
      }

      collection.current?.clear();

      collection.current = editor.current.createDecorationsCollection(
        value
          .split('\n')
          .map((line, index) => {
            if (!line) {
              return null;
            }

            const matchedKey = Object.keys(typesDetection).find(key => line.trimStart().startsWith(key + ':'));

            if (matchedKey) {
              return {
                range: new monaco.Range(index + 1, line.length + 1, index + 1, line.length + 1),
                options: { afterContentClassName: `typehint ${matchedKey}` }
              };
            }

            return {
              range: new monaco.Range(index + 1, line.length + 1, index + 1, line.length + 1),
              options: { afterContentClassName: `typehint ${guessType(line) ?? 'error'}` }
            };
          })
          .filter(decoration => !!decoration)
      );
    },
    [guessType, monaco, typesDetection]
  );

  const options: editor.IStandaloneEditorConstructionOptions = useMemo(
    () => ({
      automaticLayout: true,
      readOnly: !setQuery || loading,
      minimap: { enabled: false },
      overviewRulerBorder: false,
      renderLineHighlight: 'gutter',
      autoClosingBrackets: 'always',
      scrollbar: {
        horizontal: 'hidden'
      },
      fontSize: 17,
      lineHeight: 19,
      lineDecorationsWidth: 8,
      lineNumbersMinChars: 2,
      showFoldingControls: 'never',
      scrollBeyondLastLine: false,
      glyphMargin: false,
      overviewRulerLanes: 0,
      lineNumbers: 'off',
      links: false
    }),
    [setQuery, loading]
  );

  return (
    <Card
      variant="outlined"
      sx={[
        {
          width: '100%',
          p: 1,
          '& .typehint::after': {
            pl: 2,
            opacity: 0.5,
            color: theme.palette.text.secondary,
            fontWeight: 'bold'
          },
          '& .typehint.error::after': {
            color: theme.palette.error.main,
            content: '"unknown"'
          }
        },
        ...Object.keys(typesDetection).map(_type => ({ [`& .${_type}::after`]: { content: `"${_type}"` } }))
      ]}
    >
      <Editor
        height={height}
        width={width}
        theme={theme.palette.mode === 'light' ? 'clue' : 'clue-dark'}
        value={query}
        onChange={value => {
          setQuery(value);
          calculateAnnotations(value);
        }}
        beforeMount={beforeEditorMount}
        onMount={_editor => (editor.current = _editor)}
        options={options}
      />
    </Card>
  );
};

export default memo(QueryInput);
