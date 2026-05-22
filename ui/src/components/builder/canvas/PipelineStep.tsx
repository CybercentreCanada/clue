import { useDroppable } from '@dnd-kit/core';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Delete, DragIndicator } from '@mui/icons-material';
import { Box, Card, CardContent, Chip, IconButton, Stack, Typography } from '@mui/material';
import type { FC } from 'react';
import { BLOCK_DEFINITIONS, CATEGORY_COLORS } from '../data/blockDefinitions';
import type { PipelineStep as PipelineStepType } from '../types';

interface PipelineStepProps {
  step: PipelineStepType;
  selected: boolean;
  dragOverId: string | null;
  onSelect: (instanceId: string) => void;
  onDelete: (instanceId: string) => void;
  renderChildren?: (parentStep: PipelineStepType) => React.ReactNode;
}

const NESTABLE_CHIP_COLOR = '#00897b';

const PipelineStep: FC<PipelineStepProps> = ({ step, selected, dragOverId, onSelect, onDelete, renderChildren }) => {
  const definition = BLOCK_DEFINITIONS.find(b => b.id === step.definitionId);
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: step.instanceId
  });

  const childDropId = `children:${step.instanceId}`;
  const { setNodeRef: setChildDropRef, isOver: isChildOver } = useDroppable({ id: childDropId });

  const categoryColor = CATEGORY_COLORS[definition?.category] ?? '#757575';
  const isWrapper = definition?.isWrapper ?? false;
  const isDropTarget = dragOverId === childDropId || isChildOver;

  const style = {
    transform: CSS.Transform.toString(transform),
    transition
  };

  return (
    <Card
      ref={setNodeRef}
      style={style}
      sx={{
        mb: 1.5,
        borderLeft: `4px solid ${categoryColor}`,
        opacity: isDragging ? 0.5 : 1,
        outline: selected ? `2px solid ${categoryColor}` : 'none',
        cursor: 'pointer'
      }}
      onClick={e => {
        e.stopPropagation();
        onSelect(step.instanceId);
      }}
    >
      <CardContent sx={{ py: 1, px: 1.5, '&:last-child': { pb: 1 } }}>
        <Stack direction="row" alignItems="center" spacing={1}>
          <IconButton size="small" sx={{ cursor: 'grab' }} {...attributes} {...listeners}>
            <DragIndicator fontSize="small" />
          </IconButton>
          <Typography variant="body2" fontWeight="bold" sx={{ flex: 1 }}>
            {definition?.label ?? step.definitionId}
          </Typography>
          {isWrapper && (
            <Chip
              label="nestable"
              size="small"
              variant="outlined"
              sx={{ fontSize: '0.65rem', height: 20, color: NESTABLE_CHIP_COLOR, borderColor: NESTABLE_CHIP_COLOR }}
            />
          )}
          <Chip
            label={definition?.category}
            size="small"
            sx={{ bgcolor: `${categoryColor}22`, color: categoryColor }}
          />
          <IconButton
            size="small"
            onClick={e => {
              e.stopPropagation();
              onDelete(step.instanceId);
            }}
          >
            <Delete fontSize="small" />
          </IconButton>
        </Stack>

        {isWrapper && (
          <Box
            ref={setChildDropRef}
            sx={{
              mt: 1,
              ml: 3,
              pl: 2,
              py: 1,
              borderLeft: `2px dashed ${isDropTarget ? categoryColor : `${categoryColor}66`}`,
              borderRadius: 1,
              minHeight: 48,
              bgcolor: isDropTarget ? `${categoryColor}0a` : 'transparent',
              transition: 'all 0.15s ease'
            }}
          >
            {renderChildren?.(step)}
            {step.children.length === 0 && (
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ py: 1, display: 'block', fontStyle: 'italic' }}
              >
                {isDropTarget ? '↓ Drop here' : 'Drag blocks here'}
              </Typography>
            )}
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default PipelineStep;
