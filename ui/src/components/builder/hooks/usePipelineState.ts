import { arrayMove } from '@dnd-kit/sortable';
import { useReducer } from 'react';
import { BLOCK_DEFINITIONS } from '../data/blockDefinitions';
import type { PipelineState, PipelineStep } from '../types';

export type PipelineAction =
  | { type: 'ADD_STEP'; definitionId: string; parentId?: string }
  | { type: 'MOVE_STEP'; from: number; to: number; parentId?: string }
  | { type: 'DELETE_STEP'; instanceId: string }
  | { type: 'UPDATE_STEP_CONFIG'; instanceId: string; patch: Record<string, unknown> }
  | { type: 'SET_INDICATOR_TYPE'; indicatorType: string }
  | { type: 'SELECT_STEP'; instanceId: string | null }
  | { type: 'LOAD_MANIFEST'; indicatorType: string; steps: PipelineStep[] };

const initialState: PipelineState = {
  indicatorType: 'ip',
  steps: [],
  selectedStepId: null
};

const createStep = (definitionId: string): PipelineStep | null => {
  const def = BLOCK_DEFINITIONS.find(b => b.id === definitionId);
  if (!def) return null;

  const defaultConfig: Record<string, unknown> = {};
  for (const field of def.configFields) {
    if (field.defaultValue !== undefined) {
      defaultConfig[field.key] = field.defaultValue;
    }
  }

  return {
    instanceId: crypto.randomUUID(),
    definitionId,
    config: defaultConfig,
    children: []
  };
};

/** Recursively apply a transformation to a step tree. */
const mapSteps = (steps: PipelineStep[], fn: (s: PipelineStep) => PipelineStep | null): PipelineStep[] => {
  const result: PipelineStep[] = [];
  for (const step of steps) {
    const mapped = fn(step);
    if (mapped) {
      result.push({ ...mapped, children: mapSteps(mapped.children, fn) });
    }
  }
  return result;
};

/** Find a step anywhere in the tree. */
const findStep = (steps: PipelineStep[], id: string): PipelineStep | null => {
  for (const step of steps) {
    if (step.instanceId === id) return step;
    const found = findStep(step.children, id);
    if (found) return found;
  }
  return null;
};

/** Collect all instanceIds (flat). */
const allIds = (steps: PipelineStep[]): string[] => {
  return steps.flatMap(s => [s.instanceId, ...allIds(s.children)]);
};

/** Recursively assign fresh instanceIds to imported steps. */
const assignFreshIds = (steps: PipelineStep[]): PipelineStep[] =>
  steps.map(s => ({
    ...s,
    instanceId: crypto.randomUUID(),
    children: assignFreshIds(s.children)
  }));

const pipelineReducer = (state: PipelineState, action: PipelineAction): PipelineState => {
  switch (action.type) {
    case 'ADD_STEP': {
      const newStep = createStep(action.definitionId);
      if (!newStep) return state;

      if (action.parentId) {
        // Add as child of a wrapper block
        return {
          ...state,
          steps: mapSteps(state.steps, s =>
            s.instanceId === action.parentId ? { ...s, children: [...s.children, newStep] } : s
          )
        };
      }
      return { ...state, steps: [...state.steps, newStep] };
    }

    case 'MOVE_STEP': {
      if (action.parentId) {
        return {
          ...state,
          steps: mapSteps(state.steps, s =>
            s.instanceId === action.parentId ? { ...s, children: arrayMove(s.children, action.from, action.to) } : s
          )
        };
      }
      return { ...state, steps: arrayMove(state.steps, action.from, action.to) };
    }

    case 'DELETE_STEP': {
      const selectedStepId = state.selectedStepId === action.instanceId ? null : state.selectedStepId;
      // Remove from top level
      let steps = state.steps.filter(s => s.instanceId !== action.instanceId);
      // Remove from children recursively
      steps = mapSteps(steps, s => ({
        ...s,
        children: s.children.filter(c => c.instanceId !== action.instanceId)
      }));
      return { ...state, steps, selectedStepId };
    }

    case 'UPDATE_STEP_CONFIG': {
      return {
        ...state,
        steps: mapSteps(state.steps, s =>
          s.instanceId === action.instanceId ? { ...s, config: { ...s.config, ...action.patch } } : s
        )
      };
    }

    case 'SET_INDICATOR_TYPE': {
      return { ...state, indicatorType: action.indicatorType };
    }

    case 'SELECT_STEP': {
      return { ...state, selectedStepId: action.instanceId };
    }

    case 'LOAD_MANIFEST': {
      return {
        indicatorType: action.indicatorType,
        steps: assignFreshIds(action.steps),
        selectedStepId: null
      };
    }

    default:
      return state;
  }
};

export { allIds, findStep };

const usePipelineState = () => {
  const [state, dispatch] = useReducer(pipelineReducer, initialState);
  return { state, dispatch };
};

export default usePipelineState;
