/// <reference types="vite/client" />

import type {
  ClueDatabase,
  ClueDatabaseCollections,
  SelectorCollection,
  SelectorCollectionMethods,
  SelectorDocMethods,
  SelectorDocType,
  SelectorDocument,
  StatusCollection,
  StatusCollectionMethods,
  StatusDocMethods,
  StatusDocType,
  StatusDocument
} from 'lib/database/types';
import type { ActionDefinition, ActionDefinitionsResponse, ActionResult } from 'lib/types/action';
import type EnrichmentProps from 'lib/types/EnrichmentProps';
import type { FetcherDefinition, FetcherDefinitionsResponse, FetcherResult } from 'lib/types/fetcher';
import type {
  Annotation,
  BulkEnrichRequest,
  BulkEnrichResponses,
  Enrichment,
  EnrichResponse,
  EnrichResponses,
  FailedRequest,
  Selector,
  TypesDetectionResponse,
  TypesResponse,
  WithExtra
} from 'lib/types/lookup';
import type { ClueResponse } from 'lib/types/network';
import type RunningActionData from 'lib/types/RunningActionData';
import ActionForm from './components/actions/ActionForm';
import AnnotationDetailPopover from './components/AnnotationDetailPopover';
import AnnotationDetails from './components/AnnotationDetails';
import AnnotationEntry from './components/AnnotationEntry';
import AnnotationPreview from './components/AnnotationPreview';
import CountBadge from './components/CountBadge';
import EnrichedCard, { type EnrichedCardProps } from './components/EnrichedCard';
import EnrichedChip from './components/EnrichedChip';
import EnrichedTypography, { type EnrichedTypographyProps } from './components/EnrichedTypography';
import Fetcher from './components/fetchers/Fetcher';
import StatusChip from './components/fetchers/StatusChip';
import Entry from './components/group/Entry';
import Group from './components/group/Group';
import GroupControl from './components/group/GroupControl';
import SourcePicker from './components/SourcePicker';
import { SNACKBAR_EVENT_ID, type SnackbarEvents } from './data/event';
import buildDatabase from './database';
import { ClueComponentContext } from './hooks/ClueComponentContext';
import type { ClueConfigContextProps } from './hooks/ClueConfigProvider';
import { ClueConfigContext } from './hooks/ClueConfigProvider';
import { ClueDatabaseContext, type ClueDatabaseContextProps } from './hooks/ClueDatabaseContext';
import { ClueEnrichContext } from './hooks/ClueEnrichContext';
import { CluePopupContext } from './hooks/CluePopupContext';
import { ClueProvider } from './hooks/ClueProvider';
import { useClueActionsSelector, useClueEnrichSelector, useClueFetcherSelector } from './hooks/selectors';
import useClue from './hooks/useClue';
import useClueActions from './hooks/useClueActions';
import useClueConfig from './hooks/useClueConfig';
import AssessmentIcon from './icons/Assessment';
import ContextIcon from './icons/Context';
import OpinionIcon from './icons/Opinion';
import FrequencyText from './text/Frequency';

export {
  ActionForm,
  AnnotationDetailPopover,
  AnnotationDetails,
  AnnotationEntry,
  AnnotationPreview,
  AssessmentIcon,
  buildDatabase,
  ClueComponentContext,
  ClueConfigContext,
  ClueDatabaseContext,
  ClueEnrichContext,
  CluePopupContext,
  ClueProvider,
  ContextIcon,
  CountBadge,
  EnrichedCard,
  EnrichedChip,
  EnrichedTypography,
  Entry,
  Fetcher,
  FrequencyText,
  Group,
  GroupControl,
  OpinionIcon,
  SNACKBAR_EVENT_ID,
  SourcePicker,
  StatusChip,
  useClue,
  useClueActions,
  useClueActionsSelector,
  useClueConfig,
  useClueEnrichSelector,
  useClueFetcherSelector
};

export type {
  ActionDefinition,
  ActionDefinitionsResponse,
  ActionResult,
  Annotation,
  BulkEnrichRequest,
  BulkEnrichResponses,
  ClueConfigContextProps,
  ClueDatabase,
  ClueDatabaseCollections,
  ClueDatabaseContextProps,
  ClueResponse,
  EnrichedCardProps,
  EnrichedTypographyProps,
  Enrichment,
  EnrichmentProps,
  EnrichResponse,
  EnrichResponses,
  FailedRequest,
  FetcherDefinition,
  FetcherDefinitionsResponse,
  FetcherResult,
  RunningActionData,
  Selector,
  SelectorCollection,
  SelectorCollectionMethods,
  SelectorDocMethods,
  SelectorDocType,
  SelectorDocument,
  SnackbarEvents,
  StatusCollection,
  StatusCollectionMethods,
  StatusDocMethods,
  StatusDocType,
  StatusDocument,
  TypesDetectionResponse,
  TypesResponse,
  WithExtra
};

export type {
  ClueConfigContextProps as BorealisConfigContextProps,
  ClueDatabase as BorealisDatabase,
  ClueDatabaseCollections as BorealisDatabaseCollections,
  ClueDatabaseContextProps as BorealisDatabaseContextProps,
  ClueResponse as BorealisResponse
};
