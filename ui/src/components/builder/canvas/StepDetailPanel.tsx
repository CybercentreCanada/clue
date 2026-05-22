import { Box, Checkbox, Divider, Drawer, FormControlLabel, MenuItem, TextField, Typography } from '@mui/material';
import type { FC } from 'react';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { BLOCK_DEFINITIONS } from '../data/blockDefinitions';
import { renderBlockCode } from '../hooks/useCodeRenderer';
import type { PipelineStep } from '../types';
import CodeBlock from './CodeBlock';

interface StepDetailPanelProps {
  step: PipelineStep | null;
  onConfigChange: (instanceId: string, patch: Record<string, unknown>) => void;
}

const DRAWER_WIDTH = 380;

const StepDetailPanel: FC<StepDetailPanelProps> = ({ step, onConfigChange }) => {
  const { t } = useTranslation();

  const code = useMemo(() => (step ? renderBlockCode(step) : ''), [step]);

  if (!step) return null;

  const definition = BLOCK_DEFINITIONS.find(b => b.id === step.definitionId);
  if (!definition) return null;

  return (
    <Drawer
      variant="persistent"
      anchor="right"
      open
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': { width: DRAWER_WIDTH, position: 'relative' }
      }}
    >
      <Box sx={{ p: 2, overflow: 'auto' }}>
        <Typography variant="h6" gutterBottom>
          {definition.label}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {definition.description}
        </Typography>
        <Divider sx={{ my: 2 }} />

        {definition.configFields.length > 0 && (
          <>
            <Typography variant="subtitle2" gutterBottom>
              {t('route.builder.config')}
            </Typography>
            {definition.configFields.map(field => {
              const value = step.config[field.key] ?? field.defaultValue ?? '';

              if (field.type === 'boolean') {
                return (
                  <FormControlLabel
                    key={field.key}
                    control={
                      <Checkbox
                        checked={!!value}
                        onChange={e => onConfigChange(step.instanceId, { [field.key]: e.target.checked })}
                      />
                    }
                    label={field.label}
                    sx={{ mb: 1, display: 'flex' }}
                  />
                );
              }

              if (field.type === 'select' && field.options) {
                return (
                  <TextField
                    key={field.key}
                    select
                    label={field.label}
                    value={value}
                    onChange={e => onConfigChange(step.instanceId, { [field.key]: e.target.value })}
                    fullWidth
                    size="small"
                    sx={{ mb: 2 }}
                  >
                    {field.options.map(opt => (
                      <MenuItem key={opt} value={opt}>
                        {opt}
                      </MenuItem>
                    ))}
                  </TextField>
                );
              }

              return (
                <TextField
                  key={field.key}
                  label={field.label}
                  value={value}
                  onChange={e => onConfigChange(step.instanceId, { [field.key]: e.target.value })}
                  fullWidth
                  size="small"
                  multiline={field.key === 'vars'}
                  minRows={field.key === 'vars' ? 3 : undefined}
                  sx={{ mb: 2 }}
                />
              );
            })}
            <Divider sx={{ my: 2 }} />
          </>
        )}

        <Typography variant="subtitle2" gutterBottom>
          {t('route.builder.code')}
        </Typography>
        <CodeBlock code={code} />
      </Box>
    </Drawer>
  );
};

export default StepDetailPanel;
