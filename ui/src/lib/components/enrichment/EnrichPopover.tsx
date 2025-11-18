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
import { useClueComponentSelector, useClueEnrichSelector } from 'lib/hooks/selectors';
import type { Selector } from 'lib/types/lookup';
import capitalize from 'lodash-es/capitalize';
import type { FC } from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import Iconified from '../display/icons/Iconified';

const EnrichPopover: FC<{
  size?: 'small' | 'medium';
  show?: boolean;
  multiples?: boolean;
  selector: Selector;
}> = ({ show = false, size = 'small', selector }) => {
  const { t } = useClueComponentSelector(ctx => ctx.i18next);
  const theme = useTheme();
  const availableSources = useClueEnrichSelector(ctx => ctx.availableSources);
  const _enrich = useClueEnrichSelector(ctx => ctx.enrich);

  const [showEnrichMenu, setShowEnrichMenu] = useState(show);
  const [loading, setLoading] = useState(false);

  const enrichEl = useRef<HTMLElement>(null);

  const enrich = useCallback(
    async (_source: string) => {
      setLoading(true);
      try {
        await _enrich(selector.type, selector.value, {
          classification: selector.classification,
          timeout: 30,
          force: true,
          noCache: true,
          sources: [_source],
          append: true
        });
      } finally {
        setLoading(false);
      }
    },
    [_enrich, selector.classification, selector.type, selector.value]
  );

  useEffect(() => {
    setShowEnrichMenu(show);
  }, [show]);

  return (
    <>
      {size === 'small' ? (
        <Tooltip ref={enrichEl} title={t('enrich')}>
          <span style={{ alignSelf: 'center' }}>
            <IconButton
              onClick={() => setShowEnrichMenu(true)}
              disabled={Object.keys(availableSources).length < 1 || loading}
              color="info"
            >
              {loading ? <CircularProgress color="info" size="24px" /> : <Iconified icon="ic:baseline-auto-fix-high" />}
            </IconButton>
          </span>
        </Tooltip>
      ) : (
        <Button
          ref={enrichEl as any}
          variant="outlined"
          color="info"
          disabled={Object.keys(availableSources).length < 1 || loading}
          startIcon={
            loading ? <CircularProgress color="info" size="20px" /> : <Iconified icon="ic:baseline-auto-fix-high" />
          }
          sx={{ alignSelf: 'stretch' }}
          onClick={() => setShowEnrichMenu(true)}
        >
          {t('enrich')}
        </Button>
      )}
      <Popover
        sx={{ zIndex: 2000 }}
        open={showEnrichMenu}
        disablePortal
        onClose={() => setShowEnrichMenu(false)}
        anchorEl={enrichEl.current}
        anchorOrigin={{ horizontal: 'left', vertical: 'bottom' }}
      >
        <Paper onClick={() => setShowEnrichMenu(false)}>
          <Stack divider={<Divider flexItem orientation="horizontal" />}>
            {availableSources.map(_source => (
              <Box
                key={_source}
                sx={{
                  px: 3,
                  py: 1,
                  cursor: 'pointer',
                  transition: theme.transitions.create('background-color'),
                  '&:hover': { backgroundColor: theme.palette.background.default }
                }}
                onClick={() => enrich(_source)}
              >
                <Stack>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Typography variant="body1">{_source.split('-').map(capitalize).join(' ')}</Typography>
                    {/* TODO: Expose additional source information */}
                    {/* <ClassificationChip size="small" classification={action.classification} /> */}
                  </Stack>
                </Stack>
              </Box>
            ))}
          </Stack>
        </Paper>
      </Popover>
    </>
  );
};

export default EnrichPopover;
