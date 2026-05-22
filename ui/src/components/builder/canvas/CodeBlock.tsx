import { Editor } from '@monaco-editor/react';
import { Box, useTheme } from '@mui/material';
import type { editor } from 'monaco-editor';
import type { FC } from 'react';
import { useMemo } from 'react';

interface CodeBlockProps {
  code: string;
  height?: string;
}

const CodeBlock: FC<CodeBlockProps> = ({ code, height = '200px' }) => {
  const theme = useTheme();

  const options: editor.IStandaloneEditorConstructionOptions = useMemo(
    () => ({
      readOnly: true,
      automaticLayout: true,
      minimap: { enabled: false },
      overviewRulerBorder: false,
      renderLineHighlight: 'none',
      scrollBeyondLastLine: false,
      lineNumbers: 'on',
      lineNumbersMinChars: 3,
      glyphMargin: false,
      folding: true,
      scrollbar: { horizontal: 'hidden', vertical: 'auto' },
      fontSize: 13,
      domReadOnly: true
    }),
    []
  );

  return (
    <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, overflow: 'hidden' }}>
      <Editor
        height={height}
        language="python"
        theme={theme.palette.mode === 'light' ? 'vs' : 'vs-dark'}
        value={code}
        options={options}
      />
    </Box>
  );
};

export default CodeBlock;
