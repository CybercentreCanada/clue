import type { JsonFormsCore, JsonSchema } from '@jsonforms/core';
import { materialCells, materialRenderers } from '@jsonforms/material-renderers';
import { JsonForms } from '@jsonforms/react';
import { Box, Button, CircularProgress, Collapse, Divider, Modal, Paper, Stack, Typography } from '@mui/material';
import type { JSONSchema7 } from 'json-schema';
import Iconified from 'lib/components/display/icons/Iconified';
import JSONViewer from 'lib/components/display/json';
import { ClueComponentContext } from 'lib/hooks/ClueComponentContext';
import useClueActions from 'lib/hooks/useClueActions';
import type RunningActionData from 'lib/types/RunningActionData';
import capitalize from 'lodash-es/capitalize';
import isEqual from 'lodash-es/isEqual';
import type { FC } from 'react';
import { memo, useCallback, useMemo, useState } from 'react';
import { useContextSelector } from 'use-context-selector';
import ErrorBoundary from '../ErrorBoundary';
import { adaptSchema } from './form/schemaAdapter';

const WRAPPED_RENDERERS = materialRenderers.map(value => ({
  ...value,
  renderer: ({ ...props }) => (
    <ErrorBoundary>
      <value.renderer {...props} />
    </ErrorBoundary>
  )
}));

/**
 * The Annotation Popover is for showing a permanent popover on click with interactivity. For showing data on hover, use Annotation Popper.
 */
const ActionForm: FC<{
  runningActionData: RunningActionData;
}> = ({ runningActionData }) => {
  const { executeAction, cancelAction } = useClueActions();
  const { t } = useContextSelector(ClueComponentContext, ctx => ctx.i18next);

  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<JsonFormsCore['errors']>(null);
  const [formData, setFormData] = useState<{ [index: string]: any }>(runningActionData?.params);

  const [showFormDataJson, setShowFormDataJson] = useState<boolean>(false);

  const formSchema = useMemo(
    () =>
      runningActionData?.action
        ? { ...adaptSchema(runningActionData.action.params), ...(runningActionData.action.extra_schema ?? {}) }
        : null,
    [runningActionData?.action]
  );

  const uiSchema = useMemo(
    () => ({
      type: 'VerticalLayout',
      elements: Object.entries(formSchema?.properties ?? {})
        .sort(([a_key, a_ent], [b_key, b_ent]) => {
          if (!!(a_ent as any).order || !!(b_ent as any).order) {
            return (a_ent as any).order - (b_ent as any).order;
          } else {
            return +formSchema?.required.includes(a_key) - +formSchema?.required.includes(b_key);
          }
        })
        .map(([key, value]) => ({
          type: 'Control',
          scope: `#/properties/${key}`,
          options: {
            autocomplete: !!(value as JSONSchema7).enum,
            showUnfocusedDescription: true,
            ...(value as any).options
          },
          rule: (value as any).rule
        }))
    }),
    [formSchema?.properties, formSchema?.required]
  );

  const execute = useCallback(async () => {
    try {
      setLoading(true);
      const options: Record<string, any> = {};

      if (runningActionData?.onComplete) {
        options.onComplete = runningActionData?.onComplete;
      }

      if (runningActionData?.timeout) {
        options.timeout = runningActionData?.timeout;
      }

      await executeAction(runningActionData?.id, runningActionData?.selectors, formData, options);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [
    executeAction,
    runningActionData?.id,
    runningActionData?.selectors,
    runningActionData?.onComplete,
    runningActionData?.timeout,
    formData
  ]);

  if (!runningActionData?.action) {
    return;
  }

  try {
    return (
      <Modal open sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClose={cancelAction}>
        <Paper
          sx={{ maxHeight: '80%', maxWidth: '80%', height: '100%', px: 2, pt: 2, minWidth: '750px', overflow: 'auto' }}
        >
          <Stack
            spacing={1}
            height="100%"
            sx={{
              '.MuiFormHelperText-root': {
                marginLeft: '0 !important',
                '&:last-of-type': { mb: 3 }
              }
            }}
          >
            <Stack direction="row" spacing={1}>
              <Stack direction="column" spacing={1}>
                <Typography variant="h5">
                  {t('actions.executing')}{' '}
                  {runningActionData?.action.id.replace(/_/g, ' ').split(' ').map(capitalize).join(' ')}
                </Typography>
                {runningActionData?.action.summary && (
                  <Typography variant="body1" color="text.secondary" sx={{ pb: 1.5 }}>
                    {runningActionData?.action.summary}
                  </Typography>
                )}
              </Stack>
              <Box flex={1} />
              <Box alignContent="end">
                <Button
                  variant="outlined"
                  onClick={() => setShowFormDataJson(prev => !prev)}
                  startIcon={
                    <Box
                      component="span"
                      sx={theme => ({
                        transition: theme.transitions.create('transform'),
                        transform: showFormDataJson ? 'rotate(180deg)' : 'rotate(0deg)'
                      })}
                    >
                      <Iconified icon="ic:baseline-keyboard-double-arrow-right" />
                    </Box>
                  }
                >
                  {!showFormDataJson ? t('actions.json.show') : t('actions.json.hide')}
                </Button>
              </Box>
            </Stack>
            <Divider orientation="horizontal" variant="middle" />
            <Box pt={1.5} />
            <Stack flexGrow={1} direction="row" spacing={1}>
              <Stack direction="column" flexGrow={1}>
                <ErrorBoundary>
                  <JsonForms
                    schema={formSchema as JsonSchema}
                    uischema={uiSchema}
                    renderers={WRAPPED_RENDERERS}
                    cells={materialCells}
                    data={formData}
                    onChange={({ data, errors: _errors }) => {
                      if (!isEqual(data, formData)) {
                        setFormData(data);
                      }

                      setErrors(_errors);
                    }}
                    config={{}}
                  />
                </ErrorBoundary>
                <Stack direction="row" spacing={1} pb={1}>
                  <div style={{ flex: 1 }} />
                  <Button color="error" variant="outlined" onClick={cancelAction}>
                    {t('cancel')}
                  </Button>
                  <Button
                    color="success"
                    variant="outlined"
                    disabled={loading || errors?.length > 0}
                    onClick={execute}
                    endIcon={loading && <CircularProgress color="inherit" size={18} />}
                  >
                    {t('actions.execute')}
                  </Button>
                </Stack>
              </Stack>

              <Collapse orientation="horizontal" in={showFormDataJson} unmountOnExit mountOnEnter>
                <Stack direction="row" height="100%" spacing={1}>
                  <Divider orientation="vertical" />
                  <Stack>
                    <Typography variant="h5">{t('action.data')}</Typography>
                    <Box width={600} height="100%">
                      <JSONViewer data={formData} slotProps={{ stack: { height: '100%' }, json: { name: false } }} />
                    </Box>
                  </Stack>
                </Stack>
              </Collapse>
            </Stack>
          </Stack>
        </Paper>
      </Modal>
    );
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn(e);

    return null;
  }
};

export default memo(ActionForm);
