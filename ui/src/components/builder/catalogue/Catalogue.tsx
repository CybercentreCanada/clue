import { ExpandMore } from '@mui/icons-material';
import SearchIcon from '@mui/icons-material/Search';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  InputAdornment,
  TextField,
  Typography
} from '@mui/material';
import Fuse from 'fuse.js';
import type { FC } from 'react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BLOCK_DEFINITIONS } from '../data/blockDefinitions';
import type { BlockDefinition } from '../types';
import CatalogueItem from './CatalogueItem';

const Catalogue: FC = () => {
  const { t } = useTranslation();
  const [search, setSearch] = useState('');

  const fuse = useMemo(
    () =>
      new Fuse(BLOCK_DEFINITIONS, {
        keys: ['label', 'category', 'description'],
        threshold: 0.3
      }),
    []
  );

  const filtered: BlockDefinition[] = useMemo(() => {
    if (!search.trim()) return BLOCK_DEFINITIONS;
    return fuse.search(search).map(r => r.item);
  }, [search, fuse]);

  const grouped = useMemo(() => {
    const map = new Map<string, BlockDefinition[]>();
    for (const def of filtered) {
      const list = map.get(def.category) ?? [];
      list.push(def);
      map.set(def.category, list);
    }
    return map;
  }, [filtered]);

  return (
    <Box sx={{ width: 300, minWidth: 300, borderRight: 1, borderColor: 'divider', overflow: 'auto', p: 2 }}>
      <Typography variant="h6" gutterBottom>
        {t('route.builder.catalogue')}
      </Typography>
      <TextField
        size="small"
        fullWidth
        placeholder={t('route.builder.search')}
        value={search}
        onChange={e => setSearch(e.target.value)}
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            )
          }
        }}
        sx={{ mb: 2 }}
      />
      {[...grouped.entries()].map(([category, defs]) => (
        <Accordion key={category} defaultExpanded disableGutters elevation={0}>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="subtitle2">{category}</Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ p: 1 }}>
            {defs.map(def => (
              <CatalogueItem key={def.id} definition={def} />
            ))}
          </AccordionDetails>
        </Accordion>
      ))}
    </Box>
  );
};

export default Catalogue;
