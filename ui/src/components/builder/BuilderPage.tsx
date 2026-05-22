import type { DragEndEvent, DragOverEvent, DragStartEvent } from '@dnd-kit/core';
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  pointerWithin,
  useSensor,
  useSensors
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { Box, MenuItem, Paper, Tab, Tabs, TextField, Typography } from '@mui/material';
import type { FC, SyntheticEvent } from 'react';
import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import CodePreviewPanel from './canvas/CodePreviewPanel';
import PipelineCanvas from './canvas/PipelineCanvas';
import StepDetailPanel from './canvas/StepDetailPanel';
import Catalogue from './catalogue/Catalogue';
import { BLOCK_DEFINITIONS } from './data/blockDefinitions';
import usePipelineState, { findStep } from './hooks/usePipelineState';

const INDICATOR_TYPES = ['ip', 'domain', 'hash', 'url'];

const BuilderPage: FC = () => {
  const { t } = useTranslation();
  const { state, dispatch } = usePipelineState();
  const [activeDragLabel, setActiveDragLabel] = useState<string | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      const { active } = event;
      const data = active.data.current;

      if (data?.type === 'catalogue') {
        const def = BLOCK_DEFINITIONS.find(b => b.id === data.definitionId);
        setActiveDragLabel(def?.label ?? null);
      } else {
        const step = findStep(state.steps, String(active.id));
        if (step) {
          const def = BLOCK_DEFINITIONS.find(b => b.id === step.definitionId);
          setActiveDragLabel(def?.label ?? step.definitionId);
        }
      }
    },
    [state.steps]
  );

  const handleDragOver = useCallback((event: DragOverEvent) => {
    setDragOverId(event.over ? String(event.over.id) : null);
  }, []);

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveDragLabel(null);
      setDragOverId(null);
      const { active, over } = event;
      if (!over) return;

      const activeData = active.data.current;
      const overId = String(over.id);

      // Catalogue → Canvas drop
      if (activeData?.type === 'catalogue') {
        // Check if dropping into a wrapper's child zone (id = "children:<parentId>")
        if (overId.startsWith('children:')) {
          const parentId = overId.slice('children:'.length);
          dispatch({ type: 'ADD_STEP', definitionId: activeData.definitionId, parentId });
          return;
        }

        // Drop onto root canvas or onto an existing step card → add to root
        if (overId === 'pipeline-canvas' || findStep(state.steps, overId)) {
          dispatch({ type: 'ADD_STEP', definitionId: activeData.definitionId });
        }
        return;
      }

      // Canvas reorder
      if (active.id !== over.id) {
        const oldIndex = state.steps.findIndex(s => s.instanceId === active.id);
        const newIndex = state.steps.findIndex(s => s.instanceId === over.id);
        if (oldIndex !== -1 && newIndex !== -1) {
          dispatch({ type: 'MOVE_STEP', from: oldIndex, to: newIndex });
        }
      }
    },
    [state.steps, dispatch]
  );

  const handleDragCancel = useCallback(() => {
    setActiveDragLabel(null);
    setDragOverId(null);
  }, []);

  const handleTabChange = useCallback((_: SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  }, []);

  const selectedStep = findStep(state.steps, state.selectedStepId ?? '') ?? null;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography variant="h5" component="h1" sx={{ mr: 'auto' }}>
          {t('route.builder')}
        </Typography>
        <TextField
          select
          label={t('route.builder.indicator')}
          value={state.indicatorType}
          onChange={e => dispatch({ type: 'SET_INDICATOR_TYPE', indicatorType: e.target.value })}
          size="small"
          sx={{ minWidth: 200 }}
        >
          {INDICATOR_TYPES.map(type => (
            <MenuItem key={type} value={type}>
              {type.toUpperCase()}
            </MenuItem>
          ))}
        </TextField>
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab} onChange={handleTabChange}>
          <Tab label={t('route.builder.tab.pipeline')} />
          <Tab label={t('route.builder.tab.code')} />
        </Tabs>
      </Box>

      {activeTab === 0 && (
        <DndContext
          sensors={sensors}
          collisionDetection={pointerWithin}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
          onDragCancel={handleDragCancel}
        >
          <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
            <Catalogue />
            <PipelineCanvas
              steps={state.steps}
              selectedStepId={state.selectedStepId}
              dragOverId={dragOverId}
              onSelect={instanceId => dispatch({ type: 'SELECT_STEP', instanceId })}
              onDelete={instanceId => dispatch({ type: 'DELETE_STEP', instanceId })}
            />
            <StepDetailPanel
              step={selectedStep}
              onConfigChange={(instanceId, patch) => dispatch({ type: 'UPDATE_STEP_CONFIG', instanceId, patch })}
            />
          </Box>

          <DragOverlay>
            {activeDragLabel ? (
              <Paper sx={{ px: 2, py: 1, pointerEvents: 'none' }} elevation={4}>
                <Typography variant="body2" fontWeight="bold">
                  {activeDragLabel}
                </Typography>
              </Paper>
            ) : null}
          </DragOverlay>
        </DndContext>
      )}

      {activeTab === 1 && <CodePreviewPanel steps={state.steps} />}
    </Box>
  );
};

export default BuilderPage;
