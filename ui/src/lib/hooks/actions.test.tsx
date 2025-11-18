import { act, render, renderHook, RenderHookResult, RenderResult, waitFor } from '@testing-library/react';
import userEvent, { UserEvent } from '@testing-library/user-event';
import { hget, hpost } from 'api';
import { SNACKBAR_EVENT_ID } from 'lib/data/event';
import buildDatabase from 'lib/database';
import type { Selector } from 'lib/types/lookup';
import { describe, it } from 'vitest';
import exampleAction from '../../tests/models/action.example.json';
import { ClueActionContextType } from './ClueActionContext';
import { ClueProvider } from './ClueProvider';
import { useClueActionsSelector } from './selectors';

// Mock the API module to intercept HTTP calls during testing
vi.mock('api', { spy: true });

// Mock functions for the ClueProvider dependencies
const getToken = vi.fn(() => 'example token');
const onNetworkCall = vi.fn(conf => conf);

// Initialize test database
const database = await buildDatabase({ devMode: false, storageType: 'memory' });

// Test wrapper component that provides the action context
const Wrapper = ({ children }) => {
  return (
    <ClueProvider ready database={database} getToken={getToken} onNetworkCall={onNetworkCall}>
      {children}
    </ClueProvider>
  );
};

/**
 * Test component that simulates action execution in a React component
 * Used to test the complete action execution flow with UI interactions
 */
const TestActionExecutionElement = () => {
  const executeAction = useClueActionsSelector(ctx => ctx.executeAction);
  const cancelAction = useClueActionsSelector(ctx => ctx.cancelAction);

  const onExecute = () => {
    const value = { type: 'ip', value: '127.0.0.1' };

    executeAction('example.action', [value as any]);
  };

  const onCancel = () => {
    cancelAction();
  };

  return (
    <div>
      <button id="execute" onClick={onExecute}>
        execute
      </button>
      <button id="cancel" onClick={onCancel}>
        cancel
      </button>
    </div>
  );
};

/**
 * Test suite for action functionality
 * Tests various aspects of the action system including:
 * - Loading and accessing available actions
 * - Refreshing actions from the server
 * - Executing actions with different scenarios
 * - Error handling and validation
 * - UI interactions with action forms
 */
describe('action functionality', () => {
  beforeEach(() => {
    // Clear mock call history before each test
    vi.mocked(hget).mockClear();
    vi.mocked(hpost).mockClear();
  });

  /**
   * Test that the action context provides correct data
   * Should load available actions and show loading state correctly
   */
  it('should call useContextSelector with correct context and selector', async () => {
    const { result } = await act(async () => {
      return renderHook(
        () => useClueActionsSelector(ctx => ({ availableActions: ctx.availableActions, loading: ctx.loading })),
        { wrapper: Wrapper }
      );
    });

    expect(result.current.availableActions['example.action']).toEqual(exampleAction);
    expect(result.current.loading).toBe(false);
  });

  /**
   * Test that actions can be refreshed from the server
   * Should make API call with proper authentication and return updated actions
   */
  it('should allow refreshing the list of actions', async () => {
    const { result } = await act(async () => {
      return renderHook(() => useClueActionsSelector(ctx => ctx.refreshActions), { wrapper: Wrapper });
    });

    vi.mocked(hget).mockClear();

    const actions = await act(async () => await result.current());

    expect(actions).toEqual({ 'example.action': exampleAction });

    expect(hget).toHaveBeenCalledOnce();
    expect(hget).toBeCalledWith(
      '/api/v1/actions',
      null,
      expect.objectContaining({ headers: { Authorization: 'Bearer example token' } })
    );
  });

  /**
   * Tests for action execution functionality
   * Covers different execution scenarios and edge cases
   */
  describe('executeAction', () => {
    /**
     * Tests for basic action execution scenarios
     * Covers simple execution flows without complex UI interactions
     */
    describe('Basic Usage', () => {
      const value: Selector = { type: 'ip', value: '127.0.0.1' };

      let hook: RenderHookResult<ClueActionContextType['executeAction'], any>;
      beforeEach(async () => {
        hook = await act(async () => {
          return renderHook(() => useClueActionsSelector(ctx => ctx.executeAction), { wrapper: Wrapper });
        });
      });

      /**
       * Test successful execution of a simple action
       * Should make proper API call with correct payload and authentication
       */
      it('should allow the execution of simple actions', async () => {
        await act(() => hook.result.current('example.action', [value], { value: 'example' }));

        expect(hpost).toHaveBeenCalledOnce();
        expect(hpost).toBeCalledWith(
          '/api/v1/actions/execute/example/action',
          {
            selector: value,
            selectors: [],
            value: 'example'
          },
          expect.objectContaining({ headers: { Authorization: 'Bearer example token' } })
        );
      });

      /**
       * Test validation when trying to skip the menu with incomplete data
       * Should throw an error if skipMenu is true but form is not valid
       */
      it('should raise an exception if forced to skip the menu when payload is invalid', async () => {
        const execution = act(() => hook.result.current('example.action', [value as any], {}, { skipMenu: true }));

        expect(execution).rejects.toThrow(new Error('Form is not completed'));
      });

      /**
       * Test handling of pivot format results
       * Should attempt to open a new window when the action result is a pivot
       */
      it('should attempt to open a new window if the output is a pivot', async () => {
        vi.stubGlobal('open', vi.fn());

        vi.mocked(hpost).mockImplementationOnce(() =>
          Promise.resolve({
            outcome: 'success',
            link: 'http://example.com',
            format: 'pivot',
            summary: 'great success',
            output: 'https://example.com'
          })
        );

        await act(() => hook.result.current('example.action', [value], { value: 'example' }));

        expect(window.open).toBeCalled();

        vi.mocked(window.open).mockRestore();
      });
    });

    /**
     * Tests for complex action execution scenarios
     * Covers UI interactions, form handling, and error scenarios
     * Uses a rendered component to test the complete user flow
     */
    describe('Complex Action', () => {
      let rendered: RenderResult;
      let user: UserEvent;
      beforeEach(async () => {
        rendered = await act(async () => {
          user = userEvent.setup();

          const _rendered = await render(
            <Wrapper>
              <TestActionExecutionElement />
            </Wrapper>
          );

          return _rendered;
        });
      });

      /**
       * Test the action form flow when payload validation fails
       * Should open form, allow user input, then execute when form is complete
       */
      it('should open the action form if payload is invalid, allowing the user to edit the request', async () => {
        // Simulate clicking the execute button to trigger the action
        await act(async () => {
          (await rendered.findByTestId('execute')).click();
        });

        // The action form should open because the payload is invalid
        expect(rendered.getByText('actions.execute')).toBeInTheDocument();

        // Find the value input field in the form
        const valueInput: HTMLInputElement = rendered.getByTestId('#/properties/value-input') as HTMLInputElement;

        // Simulate user clicking and typing a valid value into the input
        await act(async () => {
          await user.click(valueInput);
          await user.keyboard('example');
        });

        // Wait for the execute button to become enabled after valid input
        await waitFor(() => expect((rendered.getByText('actions.execute') as HTMLButtonElement).disabled).toBe(false));

        // Ensure the network call has not been made yet
        expect(hpost).not.toBeCalled();

        // Simulate clicking the execute button to submit the form
        await act(async () => {
          await rendered.getByText('actions.execute').click();
        });

        // Assert that the network call was made with the correct payload and headers
        expect(hpost).toHaveBeenCalledOnce();
        expect(hpost).toBeCalledWith(
          '/api/v1/actions/execute/example/action',
          {
            selector: { type: 'ip', value: '127.0.0.1' },
            selectors: [],
            value: 'example'
          },
          expect.objectContaining({ headers: { Authorization: 'Bearer example token' } })
        );

        // The form should close after successful execution
        expect(rendered.queryByText('actions.execute')).not.toBeInTheDocument();
      });

      /**
       * Test validation error handling when form is open but data is invalid
       * Should show validation error via snackbar notification
       */
      it('should raise an error if execution occurs with modal open but invalid data', async () => {
        await act(async () => {
          (await rendered.findByTestId('execute')).click();
        });

        expect(rendered.getByText('actions.execute')).toBeInTheDocument();

        let errorTriggered = false;
        const handler = (event: CustomEvent) => {
          errorTriggered = event.detail.message === 'action.error.validation';
        };
        window.addEventListener(SNACKBAR_EVENT_ID, handler);

        await act(async () => {
          (await rendered.findByTestId('execute')).click();
        });

        window.removeEventListener(SNACKBAR_EVENT_ID, handler);

        expect(errorTriggered).toBe(true);
      });

      /**
       * Test network error handling during action execution
       * Should show error notification and keep the form open for retry
       */
      it('should raise an error if a network error occurs', async () => {
        // Open the action form by clicking the execute button
        await act(async () => {
          (await rendered.findByTestId('execute')).click();
        });

        // Ensure the action form is displayed
        expect(rendered.getByText('actions.execute')).toBeInTheDocument();

        // Find the value input field in the form
        const valueInput: HTMLInputElement = rendered.getByTestId('#/properties/value-input') as HTMLInputElement;

        // Simulate user typing a valid value into the input
        await act(async () => {
          await user.click(valueInput);
          await user.keyboard('example');
        });

        // Wait for the execute button to become enabled
        await waitFor(() => expect((rendered.getByText('actions.execute') as HTMLButtonElement).disabled).toBe(false));

        // Mock the network call to fail with an error
        vi.mocked(hpost).mockImplementationOnce(() => Promise.reject('example error'));

        // Listen for the snackbar event to capture error notification
        let errorTriggered = false;
        const handler = (event: CustomEvent) => {
          errorTriggered = event.detail.level === 'error' && event.detail.message === 'example error';
        };
        window.addEventListener(SNACKBAR_EVENT_ID, handler);

        // Attempt to execute the action, which should trigger the error
        await act(async () => {
          (await rendered.getByText('actions.execute')).click();
        });

        // Remove the event listener after execution
        window.removeEventListener(SNACKBAR_EVENT_ID, handler);

        // Assert that the error snackbar was triggered
        expect(errorTriggered).toBe(true);

        // The form should remain open for retry after the error
        expect(rendered.queryByText('actions.execute')).toBeInTheDocument();
      });

      /**
       * Test cancellation of action execution
       * Should close the action form and cancel any ongoing operations
       */
      it('should close and cancel ongoing actions if cancel is called', async () => {
        await act(async () => {
          (await rendered.findByTestId('execute')).click();
        });

        expect(rendered.getByText('actions.execute')).toBeInTheDocument();

        await act(async () => {
          (await rendered.findByTestId('cancel')).click();
        });

        expect(rendered.queryByText('actions.execute')).not.toBeInTheDocument();
      });
    });
  });
});
