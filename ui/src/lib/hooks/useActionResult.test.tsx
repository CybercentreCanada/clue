import { act, renderHook, waitFor } from '@testing-library/react';
import type { ActionDefinition, ActionResult } from 'lib/types/action';
import type { WithActionData } from 'lib/types/WithActionData';
import { describe, it } from 'vitest';
import { useActionResult } from './useActionResult';

// Mock the selectors module so we can control getActionStatus without a full provider tree
vi.mock('./selectors', () => ({
  useClueActionsSelector: vi.fn()
}));

// Mock use-context-selector so ClueComponentContext doesn't need a real provider.
// The `t` function must be a stable reference so it doesn't appear as a changed
// dependency and re-trigger the polling useEffect on every render.
vi.mock('use-context-selector', () => {
  const t = (k: string) => k;
  return {
    createContext: (defaultValue: any) => ({ _currentValue: defaultValue }),
    useContextSelector: vi.fn((_ctx: any, selector: any) => selector({ i18next: { t } }))
  };
});

import { useClueActionsSelector } from './selectors';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const mockAction: ActionDefinition = {
  id: 'example.action',
  name: 'Example Action',
  classification: 'U',
  params: {},
  supported_types: ['ip']
};

const makeResult = (overrides: Partial<WithActionData<ActionResult>> = {}): WithActionData<ActionResult> => ({
  actionId: 'example.action',
  action: mockAction,
  outcome: 'success',
  summary: 'done',
  ...overrides
});

// ---------------------------------------------------------------------------
// Suite
// ---------------------------------------------------------------------------

describe('useActionResult', () => {
  let getActionStatus: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    getActionStatus = vi.fn();
    vi.mocked(useClueActionsSelector).mockImplementation((selector: any) => selector({ getActionStatus }));
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  /**
   * Non-pending results should be returned as-is without triggering any polling
   */
  describe('non-pending outcomes', () => {
    it('returns the result immediately for a success outcome', () => {
      const input = makeResult({ outcome: 'success', summary: 'all good' });

      const { result } = renderHook(() => useActionResult(input));

      expect(result.current).toMatchObject({ outcome: 'success', summary: 'all good', actionId: 'example.action' });
      expect(getActionStatus).not.toHaveBeenCalled();
    });

    it('returns the result immediately for a failure outcome', () => {
      const input = makeResult({ outcome: 'failure', summary: 'broke' });

      const { result } = renderHook(() => useActionResult(input));

      expect(result.current).toMatchObject({ outcome: 'failure', summary: 'broke' });
      expect(getActionStatus).not.toHaveBeenCalled();
    });

    it('returns undefined when no result is provided', () => {
      const { result } = renderHook(() => useActionResult(undefined));

      expect(result.current).toBeUndefined();
    });

    it('does not poll when outcome is pending but task_id is missing', () => {
      const input = makeResult({ outcome: 'pending' }); // no task_id

      renderHook(() => useActionResult(input));

      expect(getActionStatus).not.toHaveBeenCalled();
    });
  });

  /**
   * Pending results with a task_id should trigger polling via getActionStatus
   */
  describe('pending outcome - polling', () => {
    it('calls getActionStatus with the correct actionId and taskId', async () => {
      const input = makeResult({ outcome: 'pending', task_id: 'task-abc' });

      getActionStatus.mockResolvedValueOnce({ outcome: 'success', summary: 'resolved' });

      await act(async () => {
        renderHook(() => useActionResult(input));
      });

      expect(getActionStatus).toHaveBeenCalledWith('example.action', 'task-abc');
    });

    it('updates to the resolved result when polling returns success', async () => {
      const input = makeResult({ outcome: 'pending', task_id: 'task-abc' });

      getActionStatus.mockResolvedValueOnce({ outcome: 'success', summary: 'resolved', output: { x: 1 } });

      const { result } = renderHook(() => useActionResult(input));

      await waitFor(() => expect(result.current?.outcome).toBe('success'));

      expect(result.current).toMatchObject({ outcome: 'success', summary: 'resolved', done: true });
    });

    it('updates to the resolved result when polling returns failure', async () => {
      const input = makeResult({ outcome: 'pending', task_id: 'task-abc' });

      getActionStatus.mockResolvedValueOnce({ outcome: 'failure', summary: 'something went wrong' });

      const { result } = renderHook(() => useActionResult(input));

      await waitFor(() => expect(result.current?.outcome).toBe('failure'));

      expect(result.current).toMatchObject({ outcome: 'failure', done: true });
    });

    it('marks the result as done when polling resolves', async () => {
      const input = makeResult({ outcome: 'pending', task_id: 'task-xyz' });

      getActionStatus.mockResolvedValueOnce({ outcome: 'success' });

      const { result } = renderHook(() => useActionResult(input));

      await waitFor(() => expect(result.current?.done).toBe(true));
    });

    it('falls back to failure with done=true when getActionStatus returns null', async () => {
      const input = makeResult({ outcome: 'pending', task_id: 'task-null' });

      getActionStatus.mockResolvedValueOnce(null);

      const { result } = renderHook(() => useActionResult(input));

      await waitFor(() => expect(result.current?.outcome).toBe('failure'));

      expect(result.current).toMatchObject({ outcome: 'failure', done: true });
    });

    it('continues polling while the status remains pending', async () => {
      const input = makeResult({ outcome: 'pending', task_id: 'task-poll' });

      getActionStatus
        .mockResolvedValueOnce({ outcome: 'pending', summary: 'still working' })
        .mockResolvedValueOnce({ outcome: 'success', summary: 'finally done' });

      // Use a very short interval so the second poll fires quickly with real timers
      const { result } = renderHook(() => useActionResult(input, 1));

      await waitFor(() => expect(result.current?.outcome).toBe('success'));

      expect(getActionStatus).toHaveBeenCalledTimes(2);
    });
  });

  /**
   * onComplete callback behaviour
   */
  describe('onComplete callback', () => {
    it('calls onComplete with the final result when polling succeeds', async () => {
      const onComplete = vi.fn();
      const input = makeResult({ outcome: 'pending', task_id: 'task-cb', onComplete });

      getActionStatus.mockResolvedValueOnce({ outcome: 'success', summary: 'great' });

      renderHook(() => useActionResult(input));

      await waitFor(() => expect(onComplete).toHaveBeenCalledOnce());

      expect(onComplete).toHaveBeenCalledWith(
        expect.objectContaining({ outcome: 'success', done: true, actionId: 'example.action' })
      );
    });

    it('calls onComplete with the final result when polling returns failure', async () => {
      const onComplete = vi.fn();
      const input = makeResult({ outcome: 'pending', task_id: 'task-cb-fail', onComplete });

      getActionStatus.mockResolvedValueOnce({ outcome: 'failure', summary: 'oops' });

      renderHook(() => useActionResult(input));

      await waitFor(() => expect(onComplete).toHaveBeenCalledOnce());

      expect(onComplete).toHaveBeenCalledWith(expect.objectContaining({ outcome: 'failure', done: true }));
    });

    it('does not call onComplete while status is still pending', async () => {
      const onComplete = vi.fn();
      const input = makeResult({ outcome: 'pending', task_id: 'task-cb-mid', onComplete });

      // First poll returns pending; use a huge interval so no retry fires during the test
      getActionStatus.mockResolvedValueOnce({ outcome: 'pending' });

      renderHook(() => useActionResult(input, 100_000));

      // Wait until the first (and only) poll has completed
      await waitFor(() => expect(getActionStatus).toHaveBeenCalledOnce());

      expect(onComplete).not.toHaveBeenCalled();
    });

    it('does not call onComplete for non-pending results', () => {
      const onComplete = vi.fn();
      const input = makeResult({ outcome: 'success', onComplete });

      renderHook(() => useActionResult(input));

      expect(onComplete).not.toHaveBeenCalled();
      expect(getActionStatus).not.toHaveBeenCalled();
    });
  });

  /**
   * The hook should reflect updated props when resultWithData changes
   */
  describe('prop updates', () => {
    it('reflects a new result when resultWithData is updated', () => {
      const first = makeResult({ outcome: 'success', summary: 'first' });
      const second = makeResult({ outcome: 'failure', summary: 'second' });

      const { result, rerender } = renderHook(({ r }) => useActionResult(r), {
        initialProps: { r: first }
      });

      expect(result.current?.summary).toBe('first');

      rerender({ r: second });

      expect(result.current?.summary).toBe('second');
    });

    it('stops polling after unmount', async () => {
      const input = makeResult({ outcome: 'pending', task_id: 'task-unmount' });
      getActionStatus.mockResolvedValue({ outcome: 'pending' });

      // 10 ms interval - fast enough to accumulate visible calls if cleanup fails
      const { unmount } = renderHook(() => useActionResult(input, 10));

      // Wait until at least the first poll has completed
      await waitFor(() => expect(getActionStatus).toHaveBeenCalledOnce());

      unmount();
      const callsAtUnmount = getActionStatus.mock.calls.length;

      // 50 ms >> 10 ms interval; further polls would accumulate if cleanup was skipped
      await new Promise(resolve => setTimeout(resolve, 50));

      expect(getActionStatus).toHaveBeenCalledTimes(callsAtUnmount);
    });
  });
});
