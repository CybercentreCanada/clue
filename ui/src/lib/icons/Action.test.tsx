import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ActionResult } from 'lib/types/action';
import type { Selector } from 'lib/types/lookup';
import type { WithActionData } from 'lib/types/WithActionData';
import { createContext } from 'use-context-selector';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ActionIcon from './Action';

// ------------------------------------------------------------------
// Mocks
// ------------------------------------------------------------------

const { mockShowInfo, mockCloseInfo, mockGetActionResults } = vi.hoisted(() => ({
  mockShowInfo: vi.fn(),
  mockCloseInfo: vi.fn(),
  mockGetActionResults: vi.fn(() => [] as WithActionData<ActionResult>[])
}));

vi.mock('lib/hooks/CluePopupContext', () => ({
  CluePopupContext: createContext({
    showInfo: mockShowInfo,
    closeInfo: mockCloseInfo,
    __detailsContent: null
  })
}));

vi.mock('lib/hooks/useClueActions', () => ({
  default: () => ({ getActionResults: mockGetActionResults })
}));

vi.mock('@iconify/react', () => ({
  Icon: ({ icon, color, ...rest }: { icon: string; color?: string; [key: string]: unknown }) => (
    <span id="action-icon" data-icon={icon} data-color={color ?? ''} {...rest} />
  )
}));

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

const selector: Selector = { type: 'ip', value: '1.2.3.4' };

const makeResult = (outcome: 'success' | 'failure', id = '1'): WithActionData<ActionResult> => ({
  outcome,
  summary: `${outcome} summary`,
  actionId: id,
  action: { id, name: `Action ${id}`, classification: 'TLP:CLEAR', params: {}, supported_types: ['ip'] }
});

function renderActionIcon({ counters = false, disableTooltip = false } = {}) {
  return render(<ActionIcon value={selector} counters={counters} disableTooltip={disableTooltip} />);
}

const SUCCESS_ICON = 'material-symbols:bookmark-check-rounded';
const FAILURE_ICON = 'material-symbols:cancel-presentation-rounded';

// ------------------------------------------------------------------
// Tests
// ------------------------------------------------------------------

describe('ActionIcon - renders nothing when no action results', () => {
  it('returns null when getActionResults returns an empty array', () => {
    mockGetActionResults.mockReturnValue([]);
    const { container } = renderActionIcon();
    expect(container).toBeEmptyDOMElement();
  });
});

describe('ActionIcon - renders the correct icon(s)', () => {
  it('renders only the success icon when all results are successes', () => {
    mockGetActionResults.mockReturnValue([makeResult('success', '1'), makeResult('success', '2')]);
    renderActionIcon();
    const icons = screen.getAllByTestId('action-icon');
    const iconNames = icons.map(i => i.getAttribute('data-icon'));
    expect(iconNames).toContain(SUCCESS_ICON);
    expect(iconNames).not.toContain(FAILURE_ICON);
  });

  it('renders only the failure icon when all results are failures', () => {
    mockGetActionResults.mockReturnValue([makeResult('failure', '1'), makeResult('failure', '2')]);
    renderActionIcon();
    const icons = screen.getAllByTestId('action-icon');
    const iconNames = icons.map(i => i.getAttribute('data-icon'));
    expect(iconNames).toContain(FAILURE_ICON);
    expect(iconNames).not.toContain(SUCCESS_ICON);
  });

  it('renders both success and failure icons when results are mixed', () => {
    mockGetActionResults.mockReturnValue([makeResult('success', '1'), makeResult('failure', '2')]);
    renderActionIcon();
    const icons = screen.getAllByTestId('action-icon');
    const iconNames = icons.map(i => i.getAttribute('data-icon'));
    expect(iconNames).toContain(SUCCESS_ICON);
    expect(iconNames).toContain(FAILURE_ICON);
  });
});

describe('ActionIcon - passes the correct selector to getActionResults', () => {
  it('calls getActionResults with the selector type, value, and classification', () => {
    mockGetActionResults.mockReturnValue([]);
    renderActionIcon();
    expect(mockGetActionResults).toHaveBeenCalledWith(selector.type, selector.value, selector.classification);
  });
});

describe('ActionIcon - tooltip interactions', () => {
  beforeEach(() => {
    mockShowInfo.mockClear();
    mockCloseInfo.mockClear();
  });

  it('calls showInfo on mouse-over of the success icon when tooltip is enabled', async () => {
    mockGetActionResults.mockReturnValue([makeResult('success')]);
    const user = userEvent.setup();
    renderActionIcon();
    const span = document.querySelector('span[style]');
    await user.hover(span);
    expect(mockShowInfo).toHaveBeenCalledWith('actionResults', expect.anything(), selector, expect.anything());
  });

  it('calls closeInfo on mouse-leave of the success icon when tooltip is enabled', async () => {
    mockGetActionResults.mockReturnValue([makeResult('success')]);
    const user = userEvent.setup();
    renderActionIcon();
    const span = document.querySelector('span[style]');
    await user.hover(span);
    await user.unhover(span);
    expect(mockCloseInfo).toHaveBeenCalledWith('actionResults', selector);
  });

  it('calls showInfo on mouse-over of the failure icon when tooltip is enabled', async () => {
    mockGetActionResults.mockReturnValue([makeResult('failure')]);
    const user = userEvent.setup();
    renderActionIcon();
    const span = document.querySelector('span[style]');
    await user.hover(span);
    expect(mockShowInfo).toHaveBeenCalledWith('actionResults', expect.anything(), selector, expect.anything());
  });

  it('does NOT call showInfo on mouse-over when disableTooltip=true', async () => {
    mockGetActionResults.mockReturnValue([makeResult('success')]);
    const user = userEvent.setup();
    renderActionIcon({ disableTooltip: true });
    const span = document.querySelector('span[style]');
    await user.hover(span);
    expect(mockShowInfo).not.toHaveBeenCalled();
  });

  it('does NOT call closeInfo with "actionResults" on mouse-leave when disableTooltip=true', async () => {
    mockGetActionResults.mockReturnValue([makeResult('success')]);
    const user = userEvent.setup();
    renderActionIcon({ disableTooltip: true });
    const span = document.querySelector('span[style]');
    await user.hover(span);
    await user.unhover(span);
    // The component calls closeInfo('context', ...) on mount when disableTooltip=true to
    // dismiss any existing tooltip — that is intentional. The onMouseLeave handler must NOT fire.
    expect(mockCloseInfo).not.toHaveBeenCalledWith('actionResults', expect.anything());
  });
});
