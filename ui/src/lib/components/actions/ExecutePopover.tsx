import { Icon } from '@iconify/react';
import {
  Box,
  Button,
  CircularProgress,
  Divider,
  IconButton,
  Paper,
  Popover,
  Stack,
  Tooltip,
  Typography,
  useTheme
} from '@mui/material';
import Iconified from 'lib/components/display/icons/Iconified';
import { ClueComponentContext } from 'lib/hooks/ClueComponentContext';
import { useClueActionsSelector } from 'lib/hooks/selectors';
import useClueConfig from 'lib/hooks/useClueConfig';
import type { Selector } from 'lib/types/lookup';
import { isAccessible } from 'lib/utils/classificationParser';
import type { FC } from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useContextSelector } from 'use-context-selector';
import ClassificationChip from '../ClassificationChip';

const ExecutePopover: FC<{
  size?: 'small' | 'medium';
  show?: boolean;
  multiples?: boolean;
  selectors: Selector[];
}> = ({ show = false, size = 'small', selectors, multiples = false }) => {
  const { t } = useContextSelector(ClueComponentContext, ctx => ctx.i18next);
  const theme = useTheme();
  const availableActions = useClueActionsSelector(ctx => ctx.availableActions);
  const refreshActions = useClueActionsSelector(ctx => ctx.refreshActions);
  const executeAction = useClueActionsSelector(ctx => ctx.executeAction);
  const loading = useClueActionsSelector(ctx => ctx.loading);
  const { config } = useClueConfig();

  const [showExecuteMenu, setShowExecuteMenu] = useState(show);

  const executeEl = useRef<HTMLElement>(null);

  const actions = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(availableActions).filter(
          ([__, action]) =>
            (!action.supported_types?.length ||
              selectors.every(value => action.supported_types.includes(value?.type))) &&
            (!multiples || action.accept_multiple || selectors.length === 1) &&
            selectors.every(value => isAccessible(action.classification, value.classification, config.c12nDef))
        )
      ),
    [availableActions, config.c12nDef, multiples, selectors]
  );

  const actionDisabled = Object.keys(actions).length < 1 || loading || selectors.length < 1;

  useEffect(() => {
    setShowExecuteMenu(show);
  }, [show]);

  useEffect(() => {
    if (showExecuteMenu) {
      refreshActions();
    }
  }, [refreshActions, showExecuteMenu]);

  return (
    <>
      {size === 'small' ? (
        <Tooltip ref={executeEl} title={t('actions.execute')}>
          <span style={{ alignSelf: 'center' }}>
            <IconButton onClick={() => setShowExecuteMenu(true)} disabled={actionDisabled} color="success">
              {loading ? <CircularProgress color="success" size="24px" /> : <Iconified icon="ic:outline-play-arrow" />}
            </IconButton>
          </span>
        </Tooltip>
      ) : (
        <Button
          ref={executeEl as any}
          variant="outlined"
          color="success"
          disabled={actionDisabled}
          startIcon={
            loading ? <CircularProgress color="success" size="20px" /> : <Iconified icon="ic:outline-play-arrow" />
          }
          sx={{ alignSelf: 'stretch' }}
          onClick={() => setShowExecuteMenu(true)}
        >
          {t('actions.execute')}
        </Button>
      )}
      <Popover
        sx={{ zIndex: 2000 }}
        open={showExecuteMenu}
        disablePortal
        onClose={() => setShowExecuteMenu(false)}
        anchorEl={executeEl.current}
        anchorOrigin={{ horizontal: 'left', vertical: 'bottom' }}
      >
        <Paper onClick={() => setShowExecuteMenu(false)}>
          <Stack divider={<Divider flexItem orientation="horizontal" />}>
            {Object.entries(actions).map(([actionId, action]) => (
              <Box
                key={actionId}
                sx={{
                  px: 3,
                  py: 1,
                  cursor: 'pointer',
                  transition: theme.transitions.create('background-color'),
                  '&:hover': { backgroundColor: theme.palette.background.default }
                }}
                onClick={() => executeAction(actionId, selectors)}
              >
                <Stack>
                  <Stack direction="row" spacing={1} alignItems="center">
                    {action.action_icon && <Icon icon={action.action_icon} />}
                    <Typography variant="body1">{action.name}</Typography>
                    <ClassificationChip size="small" classification={action.classification} />
                  </Stack>
                  {action.summary && (
                    <Typography variant="caption" color="text.secondary">
                      {action.summary}
                    </Typography>
                  )}
                </Stack>
              </Box>
            ))}
          </Stack>
        </Paper>
      </Popover>
    </>
  );
};

export default ExecutePopover;
