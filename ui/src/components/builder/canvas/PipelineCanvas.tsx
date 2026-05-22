import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { Box, Typography } from '@mui/material';
import type { FC } from 'react';
import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import type { PipelineStep as PipelineStepType } from '../types';
import PipelineStep from './PipelineStep';

interface PipelineCanvasProps {
  steps: PipelineStepType[];
  selectedStepId: string | null;
  dragOverId: string | null;
  onSelect: (instanceId: string) => void;
  onDelete: (instanceId: string) => void;
}

const PipelineCanvas: FC<PipelineCanvasProps> = ({ steps, selectedStepId, dragOverId, onSelect, onDelete }) => {
  const { t } = useTranslation();
  const { setNodeRef, isOver } = useDroppable({ id: 'pipeline-canvas' });

  const stepIds = steps.map(s => s.instanceId);
  const isRootTarget = dragOverId === 'pipeline-canvas' || isOver;

  const renderChildren = useCallback(
    (parentStep: PipelineStepType) => {
      if (parentStep.children.length === 0) return null;
      const childIds = parentStep.children.map(c => c.instanceId);
      return (
        <SortableContext items={childIds} strategy={verticalListSortingStrategy}>
          {parentStep.children.map(child => (
            <PipelineStep
              key={child.instanceId}
              step={child}
              selected={child.instanceId === selectedStepId}
              dragOverId={dragOverId}
              onSelect={onSelect}
              onDelete={onDelete}
              renderChildren={renderChildren}
            />
          ))}
        </SortableContext>
      );
    },
    [selectedStepId, dragOverId, onSelect, onDelete]
  );

  return (
    <Box
      ref={setNodeRef}
      sx={{
        flex: 1,
        p: 3,
        minHeight: 300,
        overflow: 'auto',
        border: '2px dashed',
        borderColor: isRootTarget ? 'primary.main' : steps.length === 0 ? 'divider' : 'transparent',
        borderRadius: 2,
        bgcolor: isRootTarget ? 'action.hover' : 'transparent',
        transition: 'all 0.15s ease'
      }}
    >
      {steps.length === 0 ? (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: 200 }}>
          <Typography variant="body1" color="text.secondary" fontStyle="italic">
            {isRootTarget ? '↓ Drop here to add to pipeline' : t('route.builder.empty')}
          </Typography>
        </Box>
      ) : (
        <SortableContext items={stepIds} strategy={verticalListSortingStrategy}>
          {steps.map(step => (
            <PipelineStep
              key={step.instanceId}
              step={step}
              selected={step.instanceId === selectedStepId}
              dragOverId={dragOverId}
              onSelect={onSelect}
              onDelete={onDelete}
              renderChildren={renderChildren}
            />
          ))}
        </SortableContext>
      )}
    </Box>
  );
};

export default PipelineCanvas;
