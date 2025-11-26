import { Button, Checkbox, Divider, FormControlLabel, Popover, Stack, TextField } from '@mui/material';
import { useClueComponentSelector, useClueEnrichSelector } from 'lib/hooks/selectors';
import type { FC } from 'react';
import { memo, useEffect, useState } from 'react';

/**
 * The Annotation Popover is for showing a permanent popover on click with interactivity. For showing data on hover, use Annotation Popper.
 */
const SourcePicker: FC = () => {
  const { t } = useClueComponentSelector(ctx => ctx.i18next);
  const availableSources = useClueEnrichSelector(state => state.availableSources);
  const sources = useClueEnrichSelector(state => state.sources);
  const setSources = useClueEnrichSelector(state => state.setSources);

  const [anchorEl, setAnchorEl] = useState<HTMLButtonElement | null>(null);
  const [sourceFilter, setSourceFilter] = useState<string>();

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  useEffect(() => {
    setSources(availableSources);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [availableSources]);
  const id = !!anchorEl ? 'sources-popover' : undefined;

  return (
    <>
      <Button aria-describedby={id} variant="outlined" onClick={handleClick}>
        {t('sources')} ({sources.length === availableSources.length ? t('all') : sources.length})
      </Button>
      <Popover
        id={id}
        open={!!anchorEl}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'left'
        }}
      >
        <TextField
          fullWidth
          sx={{ p: 1, width: '350px' }}
          placeholder={t('quicksearch.placeholder')}
          onChange={event => setSourceFilter(event.target.value.toLowerCase())}
        />
        <Divider orientation="horizontal" />
        <Stack spacing={0.5} m={1} sx={{ maxHeight: '500px', overflow: 'auto' }} onClick={e => e.stopPropagation()}>
          <FormControlLabel
            control={
              <Checkbox
                size="small"
                checked={sources.length === availableSources.length}
                sx={{ mr: 1 }}
                onChange={(__, checked) => {
                  setSources(checked ? availableSources : []);
                }}
              />
            }
            label={sources.length < availableSources.length ? t('sources.select.all') : t('sources.select.none')}
            sx={{ whiteSpace: 'nowrap', textTransform: 'capitalize' }}
          />
          {availableSources
            .filter(source => !sourceFilter || source.toLowerCase().includes(sourceFilter))
            .map(source => (
              <FormControlLabel
                key={source}
                control={
                  <Checkbox
                    size="small"
                    checked={sources.includes(source)}
                    onChange={(__, checked) => {
                      setSources(checked ? [...sources, source] : sources.filter(src => src !== source));
                    }}
                    sx={{ mr: 1 }}
                  />
                }
                label={source.replace(/[_-]/g, ' ')}
                sx={{ whiteSpace: 'nowrap', textTransform: 'capitalize' }}
              />
            ))}
        </Stack>
      </Popover>
    </>
  );
};

export default memo(SourcePicker);
