/* eslint-disable import/no-cycle */
/* eslint-disable no-console */
import { IconButton, Stack, Typography } from '@mui/material';
import Ajv from 'ajv';
import api from 'api';
import type { AxiosRequestConfig } from 'axios';
import ActionForm from 'lib/components/actions/ActionForm';
import ResultModal from 'lib/components/actions/ResultModal';
import Iconified from 'lib/components/display/icons/Iconified';
import ErrorBoundary from 'lib/components/ErrorBoundary';
import type { SnackbarEvents } from 'lib/data/event';
import { SNACKBAR_EVENT_ID } from 'lib/data/event';
import type { ActionDefinitionsResponse, ActionResult } from 'lib/types/action';
import type { Selector } from 'lib/types/lookup';
import type RunningActionData from 'lib/types/RunningActionData';
import type { WithActionData } from 'lib/types/WithActionData';
import { dayjs } from 'lib/utils/time';
import { safeDispatchEvent } from 'lib/utils/window';
import { isNil } from 'lodash-es';
import type { FC, PropsWithChildren } from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { createContext, useContextSelector } from 'use-context-selector';
import { ClueComponentContext } from './ClueComponentContext';
import useClue from './useClue';

const AJV = new Ajv({ removeAdditional: true, coerceTypes: true, strict: false });

export interface ClueActionContextType {
  /**
   * What actions are available to execute?
   */
  availableActions: ActionDefinitionsResponse;

  /**
   * Refresh the list of actions
   */
  refreshActions: () => Promise<ActionDefinitionsResponse>;

  /**
   * Execute an action.
   *
   * @param actionId The ID of the action to execute
   * @param type The type of the selector you're executing on
   * @param value The value of the selector
   * @param classification The clasification of the selector
   * @param params The additional arguments required by the action
   */
  executeAction: (
    actionId: string,
    values: Selector[],
    params?: { [index: string]: any },
    options?: {
      /**
       * Should the action form show up regardless of if the form is completed?
       */
      forceMenu?: boolean;

      /**
       * Should the function raise an exception instead of showing the menu if the form is not completed?
       */
      skipMenu?: boolean;

      /**
       * Callback for post-execution.
       * @param result
       * @returns The action result
       */
      onComplete?: (result: WithActionData<ActionResult>) => void;

      /**
       * how long should the action have to respond?
       */
      timeout?: number;

      /**
       * Should contextual information about the source of the action be included?
       *
       * This information includes:
       * - Exact execution time
       * - Current URL on execution
       */
      includeContext?: boolean;

      /**
       * Additional context information to include on execution. Useful for tight connections between actions and the UI.
       */
      extraContext?: Record<string, any>;
    }
  ) => Promise<void>;

  /**
   * Cancel an action pending user input.
   */
  cancelAction: () => void;

  /**
   * Get a list of the results of actions executed on a selector
   * @param type The type of the selector you're executing on
   * @param value The value of the selector
   * @param classification The clasification of the selector
   * @returns the list of results for a given selector
   */
  getActionResults: (type: string, value: string, classification?: string) => WithActionData<ActionResult>[];

  /**
   * Is there currently an action executing?
   */
  loading: boolean;
}

export const ClueActionContext = createContext<ClueActionContextType>(null);

export interface ClueActionProps {
  /**
   * The base URL that refers to the clue API. leaving this empty will forward requests to the current origin.
   */
  baseURL?: string;

  /**
   * What should the default classification be when executing actions?
   */
  classification?: string;

  /**
   * Should basic context information (execution time, current url) be included when executing an action?
   */
  includeContext?: boolean;

  /**
   * Get an access token for the clue API.
   *
   * @returns An access token valid for use with the clue API.
   */
  getToken?: () => string;

  /**
   * Add modify the Axios request configuration before the request is sent
   * @param config The existing axios request config
   */
  onNetworkCall?: (config: AxiosRequestConfig) => AxiosRequestConfig;
}

export const ClueActionProvider: FC<PropsWithChildren<ClueActionProps>> = ({
  baseURL,
  children,
  classification: defaultClassification,
  includeContext: defaultIncludeContext,
  getToken,
  onNetworkCall
}) => {
  const { t, i18n } = useContextSelector(ClueComponentContext, ctx => ctx.i18next);
  const { ready } = useClue();

  const [runningActionData, setRunningActionData] = useState<RunningActionData>(null);
  const [actionResults, setActionResults] = useState<{ [index: string]: WithActionData<ActionResult>[] }>({});
  const [showResultModal, setShowResultModal] = useState(false);
  const [lastResult, setLastResult] = useState<WithActionData<ActionResult>>(null);
  const [loading, setLoading] = useState(false);

  // Initialize the sources and type detection for the user
  const [availableActions, setAvailableActions] = useState<ActionDefinitionsResponse>({});

  const refreshActions: ClueActionContextType['refreshActions'] = useCallback(async () => {
    if (!ready) {
      return;
    }

    const headers: AxiosRequestConfig['headers'] = {};
    const token = getToken?.();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    let requestConfig: AxiosRequestConfig = { baseURL, headers };
    if (onNetworkCall) {
      requestConfig = onNetworkCall(requestConfig);
    }

    const _actions = await api.actions.get(requestConfig);

    if (_actions) {
      setAvailableActions(_actions);
    }

    return _actions;
  }, [baseURL, getToken, onNetworkCall, ready]);

  useEffect(() => {
    refreshActions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseURL, ready]);

  /**
   * Return a JSON string containing the type, value and classification of the selector.
   */
  const getHashKey = useCallback(
    (type: string, value: string, classification?: string) =>
      JSON.stringify({ type, value, classification: classification ?? defaultClassification }),
    [defaultClassification]
  );

  const executeAction: ClueActionContextType['executeAction'] = useCallback(
    async (actionId, selectors, params, options) => {
      const { forceMenu, onComplete, skipMenu, timeout, includeContext, extraContext } = {
        forceMenu: false,
        skipMenu: false,
        onComplete: null,
        timeout: null,
        includeContext: defaultIncludeContext ?? false,
        extraContext: null,
        ...options
      };

      const headers: AxiosRequestConfig['headers'] = {};
      const token = getToken?.();
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }

      if (!Object.keys(availableActions).includes(actionId)) {
        throw new Error('Invalid action id');
      }

      // Telemetry is special cased into a JSON string
      const stringifiedSelectors = selectors.map(selector =>
        selector.type === 'telemetry' ? { ...selector, value: JSON.stringify(selector.value) } : selector
      );

      const actionToRun = availableActions[actionId];

      const validator = AJV.compile(actionToRun.params);

      const validatedParams = { selectors: stringifiedSelectors, ...params };

      let context: Record<string, any> | null = null;
      if (includeContext) {
        context = {
          timestamp: dayjs().toISOString(),
          url: window.location,
          language: i18n?.language ?? 'en'
        };
      }

      if (!isNil(extraContext)) {
        context = {
          ...(context ?? {}),
          ...extraContext
        };
      }

      setLoading(true);

      if (!validator(validatedParams) || forceMenu) {
        if (skipMenu && !forceMenu) {
          console.error(`Form is not valid (${validator.errors.length} errors)`);
          throw new Error('Form is not completed');
        }

        if (runningActionData?.id === actionId) {
          console.error(`Form is not valid (${validator.errors.length} errors)`);
          safeDispatchEvent(
            new CustomEvent<SnackbarEvents>(SNACKBAR_EVENT_ID, {
              detail: {
                message: t('action.error.validation'),
                level: 'error'
              }
            })
          );
        }

        setRunningActionData({
          id: actionId,
          action: actionToRun,
          selectors: selectors,
          params: validatedParams ?? {},
          context,
          onComplete,
          timeout
        });
        return;
      }

      try {
        let requestConfig: AxiosRequestConfig = { baseURL, headers };
        if (onNetworkCall) {
          requestConfig = onNetworkCall(requestConfig);
        }
        const actionResult = await api.actions.post(
          actionId,
          stringifiedSelectors,
          validatedParams ?? {},
          context,
          { timeout },
          requestConfig
        );
        const actionResultWithData = { ...actionResult, actionId, action: actionToRun };

        onComplete?.(actionResultWithData);

        setActionResults(_results => {
          const keys = selectors.map(value => getHashKey(value.type, value.value, value.classification));

          return {
            ..._results,
            ...keys.reduce(
              (acc, key) => ({
                ...acc,
                [key]: [...(_results[key] ?? []), actionResultWithData]
              }),
              {}
            )
          };
        });

        safeDispatchEvent(
          new CustomEvent<SnackbarEvents>(SNACKBAR_EVENT_ID, {
            detail: {
              message: (
                <Stack direction="row" alignItems="center" spacing={0.5} width="100%">
                  <Typography>{actionResult.summary}</Typography>
                  {actionResult.link && (
                    <IconButton component="a" href={actionResult.link} size="small" target="_blank">
                      <Iconified icon="ic:baseline-open-in-new" fontSize="small" />
                    </IconButton>
                  )}
                </Stack>
              ),
              timeout: actionResult.link ? null : 5000,
              level: actionResult.outcome === 'success' ? 'success' : 'error',
              options: {
                style: {
                  minWidth: 0
                },
                SnackbarProps: {
                  style: {
                    minWidth: 0
                  }
                }
              }
            }
          })
        );

        if (actionResult.outcome === 'success') {
          setRunningActionData(null);
        }

        if (actionResult.format) {
          setLastResult({ ...actionResult, actionId, action: actionToRun });
          if (actionResult.format !== 'pivot') {
            setShowResultModal(true);
          } else {
            window.open(actionResult.output, '_blank', 'noreferrer');
          }
        }
      } catch (e) {
        safeDispatchEvent(
          new CustomEvent<SnackbarEvents>(SNACKBAR_EVENT_ID, {
            detail: {
              message: e.toString(),
              level: 'error'
            }
          })
        );
      } finally {
        setLoading(false);
      }
    },
    [
      availableActions,
      baseURL,
      defaultIncludeContext,
      getHashKey,
      getToken,
      i18n?.language,
      onNetworkCall,
      runningActionData?.id,
      t
    ]
  );

  const cancelAction: ClueActionContextType['cancelAction'] = useCallback(() => {
    setRunningActionData(null);
    setLoading(false);
  }, []);

  const getActionResults: ClueActionContextType['getActionResults'] = useCallback(
    (type, value, classification) => actionResults[getHashKey(type, value, classification)] ?? [],
    [actionResults, getHashKey]
  );

  const context = useMemo(
    () => ({
      availableActions,
      executeAction,
      cancelAction,
      getActionResults,
      loading,
      refreshActions
    }),
    [availableActions, cancelAction, executeAction, getActionResults, loading, refreshActions]
  );

  return (
    <ClueActionContext.Provider value={context}>
      {children}
      <ErrorBoundary>
        {runningActionData && <ActionForm runningActionData={runningActionData} />}
        <ResultModal
          show={showResultModal && !!lastResult}
          result={lastResult}
          onClose={() => setShowResultModal(false)}
        />
      </ErrorBoundary>
    </ClueActionContext.Provider>
  );
};
