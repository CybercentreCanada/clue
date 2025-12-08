import type { ClueActionContextType } from 'lib/hooks/ClueActionContext';
import { ClueActionContext } from 'lib/hooks/ClueActionContext';
import type { ClueComponentContextType } from 'lib/hooks/ClueComponentContext';
import { ClueComponentContext } from 'lib/hooks/ClueComponentContext';
import { ClueEnrichContext } from 'lib/hooks/ClueEnrichContext';
import type { ClueEnrichContextType } from 'lib/hooks/ClueEnrichContextType';
import type { ClueFetcherContextType } from 'lib/hooks/ClueFetcherContext';
import { ClueFetcherContext } from 'lib/hooks/ClueFetcherContext';
import { useContextSelector } from 'use-context-selector';

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
