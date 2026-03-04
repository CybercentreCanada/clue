import { PlayArrow } from '@mui/icons-material';
import {
  Autocomplete,
  Button,
  Checkbox,
  Divider,
  FormControlLabel,
  LinearProgress,
  ListItemText,
  Stack,
  TextField,
  Typography
} from '@mui/material';
import PageCenter from 'commons/components/pages/PageCenter';
import JSONViewer from 'lib/components/display/json';
import { useClueActionsSelector } from 'lib/hooks/selectors';
import useClueConfig from 'lib/hooks/useClueConfig';
import isEmpty from 'lodash-es/isEmpty';
import uniq from 'lodash-es/uniq';
import type { FC } from 'react';
import { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

const Actions: FC = () => {
  const { t } = useTranslation();
  const { config } = useClueConfig();
  const actions = useClueActionsSelector(ctx => ctx.availableActions);
  const executeAction = useClueActionsSelector(ctx => ctx.executeAction);

  const [loading, setLoading] = useState(false);
  const [action, setAction] = useState('');
  const [classification, setClassification] = useState((config?.c12nDef?.RESTRICTED ?? '').replace(/\/\/.+/, ''));
  const [type, setType] = useState('');
  const [value, setValue] = useState('');
  const [forceMenu, setForceMenu] = useState(false);
  const [includeContext, setIncludeContext] = useState(true);
  const [useExtraContext, setUseExtraContext] = useState(false);
  const [_extraContext, setExtraContext] = useState('key: value');

  const extraContext = useMemo(
    () =>
      Object.fromEntries(
        _extraContext
          .split('\n')
          .filter(row => row.includes(': '))
          .map(row => {
            const entries = row.split(': ');
            const key = entries.shift();
            const _value = entries.join(': ');

            return [key, _value];
          })
      ),
    [_extraContext]
  );

  const runAction = useCallback(() => {
    setLoading(true);
    executeAction(action, [{ type, value, classification }], null, {
      forceMenu,
      includeContext,
      onComplete: () => setLoading(false)
    });
  }, [action, classification, executeAction, forceMenu, includeContext, type, value]);

  return (
    <PageCenter maxWidth="1800px" textAlign="left" height="100%">
      <Stack spacing={1}>
        <Typography variant="h3" sx={{ flex: 1 }}>
          {t('route.actions')}
        </Typography>
        <Divider flexItem orientation="horizontal" />
        <Typography sx={{ py: 2 }}>{t('route.actions.description')}</Typography>
        <Divider flexItem orientation="horizontal" />
        <Autocomplete
          disabled={isEmpty(actions)}
          fullWidth
          value={action}
          options={Object.keys(actions).filter(actionId => !type || actions[actionId].supported_types.includes(type))}
          onChange={(__, actionValue) => setAction(actionValue)}
          renderInput={params => <TextField {...params} sx={{ minWidth: '250px' }} label={t('route.actions.action')} />}
          renderOption={({ key, ...props }, option) => (
            <ListItemText
              key={key}
              {...(props as any)}
              sx={{ flexDirection: 'column', alignItems: 'start !important' }}
              primary={option}
              secondary={actions[option]?.summary}
            />
          )}
          sx={{ flex: 1, pt: 1 }}
          slotProps={{ paper: { sx: { minWidth: '600px' } } }}
        />
        <Autocomplete
          disabled={isEmpty(actions)}
          fullWidth
          value={classification}
          options={Object.keys(config?.c12nDef?.levels_map_lts ?? {})}
          onChange={(__, classificationValue) => setClassification(classificationValue)}
          renderInput={params => (
            <TextField {...params} sx={{ minWidth: '250px' }} label={t('page.home.classification')} />
          )}
          renderOption={(props, option) => (
            <ListItemText
              {...(props as any)}
              sx={{ flexDirection: 'column', alignItems: 'start !important' }}
              primary={option}
              secondary={config?.c12nDef?.description?.[option]}
            />
          )}
          sx={{ flex: 1 }}
          slotProps={{ paper: { sx: { minWidth: '600px' } } }}
        />
        <Stack direction="row" spacing={1}>
          <Autocomplete
            sx={{ flex: 1 }}
            value={type}
            onChange={(_, typeValue) => setType(typeValue)}
            options={uniq(
              Object.entries(actions)
                .filter(([_actionId]) => !action || _actionId === action)
                .flatMap(([_, _action]) => _action.supported_types)
            )}
            renderInput={props => <TextField {...props} label={t('route.actions.type')} />}
          />
          <TextField
            disabled={isEmpty(actions)}
            fullWidth
            sx={{ flex: 1 }}
            label={t('route.actions.value')}
            value={value}
            onChange={event => setValue(event.target.value)}
            onKeyDown={event => event.ctrlKey && event.key === 'Enter' && runAction()}
          />
        </Stack>
        <Stack direction="row" spacing={1} divider={<Divider flexItem orientation="vertical" />}>
          <FormControlLabel
            sx={{ flex: 1 }}
            control={<Checkbox checked={forceMenu} onChange={(__, checked) => setForceMenu(checked)} />}
            label={<Typography>{t('page.actions.menu.force')}</Typography>}
          />
          <FormControlLabel
            sx={{ flex: 1 }}
            control={<Checkbox checked={includeContext} onChange={(__, checked) => setIncludeContext(checked)} />}
            label={<Typography>{t('page.actions.context.include')}</Typography>}
          />
          <FormControlLabel
            sx={{ flex: 1 }}
            control={<Checkbox checked={useExtraContext} onChange={(__, checked) => setUseExtraContext(checked)} />}
            label={<Typography>{t('page.actions.context.extra')}</Typography>}
          />
        </Stack>
        <Button
          disabled={
            !(action && ((type && value && classification) || isEmpty(actions[action]?.supported_types))) || loading
          }
          startIcon={<PlayArrow />}
          variant="outlined"
          color="success"
          onClick={runAction}
        >
          {t('route.actions.submit')}
        </Button>
        <LinearProgress sx={{ opacity: !isEmpty(actions) ? 0 : 1 }} />
        {useExtraContext && (
          <>
            <Divider flexItem />
            <Typography sx={{ py: 2 }}>{t('route.actions.context.description')}</Typography>
            <Divider flexItem />
            <TextField multiline value={_extraContext} onChange={ev => setExtraContext(ev.target.value)} />
            {!isEmpty(extraContext) && <JSONViewer data={extraContext} forceCompact hideSearch />}
          </>
        )}
      </Stack>
    </PageCenter>
  );
};

export default Actions;
