import { useDraggable } from '@dnd-kit/core';
import { Box, Chip, Paper, Stack, Typography } from '@mui/material';
import type { FC } from 'react';
import { CATEGORY_COLORS } from '../data/blockDefinitions';
import type { BlockDefinition } from '../types';

interface CatalogueItemProps {
  definition: BlockDefinition;
}

const NESTABLE_CHIP_COLOR = '#00897b';

const CatalogueItem: FC<CatalogueItemProps> = ({ definition }) => {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `catalogue-${definition.id}`,
    data: { type: 'catalogue', definitionId: definition.id }
  });

  const categoryColor = CATEGORY_COLORS[definition.category] ?? '#757575';

  return (
    <Paper
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      sx={{
        p: 1.5,
        mb: 1,
        cursor: 'grab',
        opacity: isDragging ? 0.4 : 1,
        borderLeft: `4px solid ${categoryColor}`,
        '&:hover': { bgcolor: 'action.hover' }
      }}
      elevation={1}
    >
      <Stack direction="row" alignItems="center" spacing={0.5} sx={{ mb: 0.25 }}>
        <Typography variant="body2" fontWeight="bold" sx={{ flex: 1 }}>
          {definition.label}
        </Typography>
        {definition.isWrapper && (
          <Chip
            label="nestable"
            size="small"
            variant="outlined"
            sx={{ fontSize: '0.6rem', height: 18, color: NESTABLE_CHIP_COLOR, borderColor: NESTABLE_CHIP_COLOR }}
          />
        )}
      </Stack>
      <Box>
        <Typography variant="caption" color="text.secondary">
          {definition.description}
        </Typography>
      </Box>
    </Paper>
  );
};

export default CatalogueItem;
