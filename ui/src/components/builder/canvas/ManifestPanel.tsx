import { Editor } from '@monaco-editor/react';
import { Alert, Box, Button, Stack, useTheme } from '@mui/material';
import type { editor } from 'monaco-editor';
import type { FC } from 'react';
import { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BLOCK_DEFINITIONS } from '../data/blockDefinitions';
import type { PipelineStep } from '../types';

interface ManifestPanelProps {
  indicatorType: string;
  steps: PipelineStep[];
  onLoad: (indicatorType: string, steps: PipelineStep[]) => void;
}

/** Strip instanceId from steps for a clean, portable manifest. */
const toManifest = (indicatorType: string, steps: PipelineStep[]): object => {
  const stripIds = (s: PipelineStep): object => ({
    definitionId: s.definitionId,
    config: s.config,
    ...(s.children.length > 0 ? { children: s.children.map(stripIds) } : {})
  });
  return { indicatorType, steps: steps.map(stripIds) };
};

/** Validate that every step references a known block definition. */
const validateSteps = (steps: unknown[]): PipelineStep[] => {
  const knownIds = new Set(BLOCK_DEFINITIONS.map(b => b.id));
  const walk = (raw: unknown[]): PipelineStep[] =>
    raw.map((item: unknown) => {
      if (typeof item !== 'object' || item === null) throw new Error('Each step must be an object');
      const obj = item as Record<string, unknown>;
      if (typeof obj.definitionId !== 'string') throw new Error('Missing or invalid "definitionId"');
      if (!knownIds.has(obj.definitionId)) throw new Error(`Unknown block: "${obj.definitionId}"`);

      const config = (typeof obj.config === 'object' && obj.config !== null ? obj.config : {}) as Record<
        string,
        unknown
      >;
      const children = Array.isArray(obj.children) ? walk(obj.children) : [];

      return { instanceId: '', definitionId: obj.definitionId, config, children };
    });
  return walk(steps);
};

const ManifestPanel: FC<ManifestPanelProps> = ({ indicatorType, steps, onLoad }) => {
  const theme = useTheme();
  const { t } = useTranslation();

  const manifestJson = useMemo(() => JSON.stringify(toManifest(indicatorType, steps), null, 2), [indicatorType, steps]);

  const [editorValue, setEditorValue] = useState<string>(manifestJson);
  const [error, setError] = useState<string | null>(null);

  // Sync the read-only view whenever the pipeline changes externally
  // but only if the user hasn't made local edits
  const [dirty, setDirty] = useState(false);

  const displayValue = dirty ? editorValue : manifestJson;

  const handleEditorChange = useCallback((value: string | undefined) => {
    setEditorValue(value ?? '');
    setDirty(true);
    setError(null);
  }, []);

  const handleApply = useCallback(() => {
    try {
      const parsed = JSON.parse(editorValue);
      if (typeof parsed !== 'object' || parsed === null) throw new Error('Manifest must be a JSON object');
      const type = typeof parsed.indicatorType === 'string' ? parsed.indicatorType : indicatorType;
      if (!Array.isArray(parsed.steps)) throw new Error('Missing "steps" array');
      const validatedSteps = validateSteps(parsed.steps);
      onLoad(type, validatedSteps);
      setDirty(false);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid manifest');
    }
  }, [editorValue, indicatorType, onLoad]);

  const handleReset = useCallback(() => {
    setEditorValue(manifestJson);
    setDirty(false);
    setError(null);
  }, [manifestJson]);

  const options: editor.IStandaloneEditorConstructionOptions = useMemo(
    () => ({
      automaticLayout: true,
      minimap: { enabled: false },
      overviewRulerBorder: false,
      renderLineHighlight: 'gutter',
      scrollBeyondLastLine: false,
      lineNumbers: 'on',
      lineNumbersMinChars: 3,
      glyphMargin: false,
      folding: true,
      fontSize: 13,
      tabSize: 2,
      formatOnPaste: true
    }),
    []
  );

  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Stack direction="row" spacing={1} sx={{ p: 1, borderBottom: 1, borderColor: 'divider' }}>
        <Button variant="contained" size="small" disabled={!dirty} onClick={handleApply}>
          {t('route.builder.manifest.apply')}
        </Button>
        <Button variant="outlined" size="small" disabled={!dirty} onClick={handleReset}>
          {t('route.builder.manifest.reset')}
        </Button>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mx: 1, mt: 1 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ flex: 1, overflow: 'hidden' }}>
        <Editor
          height="100%"
          language="json"
          theme={theme.palette.mode === 'light' ? 'vs' : 'vs-dark'}
          value={displayValue}
          onChange={handleEditorChange}
          options={options}
        />
      </Box>
    </Box>
  );
};

export default ManifestPanel;
