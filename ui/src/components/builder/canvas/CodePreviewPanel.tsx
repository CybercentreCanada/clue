import { Editor } from '@monaco-editor/react';
import { Box, useTheme } from '@mui/material';
import type { editor } from 'monaco-editor';
import type { FC } from 'react';
import { useMemo } from 'react';
import { renderFullFile } from '../hooks/useCodeRenderer';
import type { PipelineStep } from '../types';

interface CodePreviewPanelProps {
  steps: PipelineStep[];
}

const CodePreviewPanel: FC<CodePreviewPanelProps> = ({ steps }) => {
  const theme = useTheme();
  const fullCode = useMemo(() => renderFullFile(steps), [steps]);

  const options: editor.IStandaloneEditorConstructionOptions = useMemo(
    () => ({
      readOnly: true,
      automaticLayout: true,
      minimap: { enabled: true },
      overviewRulerBorder: false,
      renderLineHighlight: 'gutter',
      scrollBeyondLastLine: false,
      lineNumbers: 'on',
      lineNumbersMinChars: 3,
      glyphMargin: false,
      folding: true,
      fontSize: 13,
      domReadOnly: true
    }),
    []
  );

  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Editor
        height="100%"
        language="python"
        theme={theme.palette.mode === 'light' ? 'vs' : 'vs-dark'}
        value={fullCode}
        options={options}
      />
    </Box>
  );
};

export default CodePreviewPanel;
