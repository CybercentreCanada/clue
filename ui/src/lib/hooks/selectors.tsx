import { useContextSelector } from 'use-context-selector';
import type { ClueActionContextType } from './ClueActionContext';
import { ClueActionContext } from './ClueActionContext';
import type { ClueComponentContextType } from './ClueComponentContext';
import { ClueComponentContext } from './ClueComponentContext';
import { ClueEnrichContext } from './ClueEnrichContext';
import type { ClueEnrichContextType } from './ClueEnrichContextType';
import type { ClueFetcherContextType } from './ClueFetcherContext';
import { ClueFetcherContext } from './ClueFetcherContext';

export const useClueFetcherSelector = <Selected,>(selector: (value: ClueFetcherContextType) => Selected): Selected => {
  return useContextSelector<ClueFetcherContextType, Selected>(ClueFetcherContext, selector);
};

export const useClueActionsSelector = <Selected,>(selector: (value: ClueActionContextType) => Selected): Selected => {
  return useContextSelector<ClueActionContextType, Selected>(ClueActionContext, selector);
};

export const useClueEnrichSelector = <Selected,>(selector: (value: ClueEnrichContextType) => Selected): Selected => {
  return useContextSelector<ClueEnrichContextType, Selected>(ClueEnrichContext, selector);
};

export const useClueComponentSelector = <Selected,>(
  selector: (value: ClueComponentContextType) => Selected
): Selected => {
  return useContextSelector<ClueComponentContextType, Selected>(ClueComponentContext, selector);
};
