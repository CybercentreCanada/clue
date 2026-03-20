import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Annotation, WithExtra } from 'lib/types/lookup';
import { createContext } from 'use-context-selector';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ContextIcon from './Context';

// ------------------------------------------------------------------
// Mocks
// ------------------------------------------------------------------

const { mockShowInfo, mockCloseInfo } = vi.hoisted(() => ({
  mockShowInfo: vi.fn(),
  mockCloseInfo: vi.fn()
}));

vi.mock('lib/hooks/CluePopupContext', () => ({
  CluePopupContext: createContext({
    showInfo: mockShowInfo,
    closeInfo: mockCloseInfo,
    __detailsContent: null
  })
}));

vi.mock('@iconify/react', () => ({
  Icon: ({ icon, ...rest }: { icon: string; [key: string]: unknown }) => (
    <span id="context-icon" data-icon={icon} {...rest} />
  )
}));

vi.mock('lib/components/AnnotationEntry', () => ({
  default: ({ annotation }: { annotation: Annotation }) => (
    <div id="annotation-entry" data-value={annotation.value as string} />
  )
}));

vi.mock('lib/components/display/icons/Iconified', () => ({
  default: ({ icon }: { icon: string }) => <span id="extra-icon" data-icon={icon} />
}));

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

const selector = { type: 'ip', value: '1.2.3.4' };

const baseAnnotation = (
  overrides: Partial<Annotation> & { icon?: string; analytic_icon?: string } = {}
): WithExtra<Annotation> => ({
  type: 'context',
  value: 'ctx-value',
  quantity: 1,
  ubiquitous: false,
  confidence: 1,
  summary: 'test',
  latency: 0,
  classification: 'TLP:CLEAR',
  analytic: 'test-analytic',
  ...overrides
});

function renderContextIcon(
  annotations: WithExtra<Annotation>[],
  { counters = false, disableTooltip = false, showExtraIcon = false, ubiquitous = false } = {}
) {
  return render(
    <ContextIcon
      annotations={annotations}
      value={selector}
      counters={counters}
      disableTooltip={disableTooltip}
      showExtraIcon={showExtraIcon}
      ubiquitous={ubiquitous}
    />
  );
}

// ------------------------------------------------------------------
// Tests
// ------------------------------------------------------------------

describe('ContextIcon - renders nothing when no context annotations', () => {
  it('returns null for an empty annotation list', () => {
    const { container } = renderContextIcon([]);
    expect(container).toBeEmptyDOMElement();
  });

  it('returns null when annotations contain only non-context types', () => {
    const { container } = renderContextIcon([baseAnnotation({ type: 'opinion' })]);
    expect(container).toBeEmptyDOMElement();
  });

  it('returns null when annotations have no matching ubiquitous flag', () => {
    const { container } = renderContextIcon([baseAnnotation({ ubiquitous: true, icon: 'mdi:test' })]);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders no visible icons when context annotations have no icon/analytic_icon and showExtraIcon=false', () => {
    renderContextIcon([baseAnnotation()]);
    expect(screen.queryByTestId('context-icon')).not.toBeInTheDocument();
    expect(screen.queryByTestId('extra-icon')).not.toBeInTheDocument();
  });
});

describe('ContextIcon - renders icons from annotation.icon', () => {
  it('renders one icon span per distinct icon value', () => {
    renderContextIcon([baseAnnotation({ icon: 'mdi:fire' }), baseAnnotation({ icon: 'mdi:ice' })]);
    const icons = screen.getAllByTestId('context-icon');
    expect(icons).toHaveLength(2);
    expect(icons.map(i => i.getAttribute('data-icon'))).toEqual(expect.arrayContaining(['mdi:fire', 'mdi:ice']));
  });

  it('groups multiple annotations with the same icon into a single icon span', () => {
    renderContextIcon([
      baseAnnotation({ icon: 'mdi:fire', value: 'a' }),
      baseAnnotation({ icon: 'mdi:fire', value: 'b' })
    ]);
    expect(screen.getAllByTestId('context-icon')).toHaveLength(1);
    expect(screen.getByTestId('context-icon').getAttribute('data-icon')).toBe('mdi:fire');
  });
});

describe('ContextIcon - renders icons from annotation.analytic_icon', () => {
  it('renders an icon span when only analytic_icon is set', () => {
    renderContextIcon([baseAnnotation({ analytic_icon: 'mdi:robot' })]);
    expect(screen.getByTestId('context-icon').getAttribute('data-icon')).toBe('mdi:robot');
  });

  it('prefers icon over analytic_icon when both are present', () => {
    renderContextIcon([baseAnnotation({ icon: 'mdi:star', analytic_icon: 'mdi:robot' })]);
    expect(screen.getByTestId('context-icon').getAttribute('data-icon')).toBe('mdi:star');
  });
});

describe('ContextIcon - showExtraIcon', () => {
  it('shows the extra newspaper icon when showExtraIcon=true and there are icon-less annotations', () => {
    renderContextIcon([baseAnnotation()], { showExtraIcon: true });
    expect(screen.getByTestId('extra-icon')).toBeInTheDocument();
  });

  it('does NOT show the extra icon when showExtraIcon=false', () => {
    renderContextIcon([baseAnnotation()], { showExtraIcon: false });
    expect(screen.queryByTestId('extra-icon')).not.toBeInTheDocument();
  });

  it('does NOT show the extra icon when all annotations have icons', () => {
    renderContextIcon([baseAnnotation({ icon: 'mdi:fire' })], { showExtraIcon: true });
    expect(screen.queryByTestId('extra-icon')).not.toBeInTheDocument();
  });

  it('shows both icon spans and the extra icon when mixed', () => {
    renderContextIcon([baseAnnotation({ icon: 'mdi:fire' }), baseAnnotation()], { showExtraIcon: true });
    expect(screen.getByTestId('context-icon')).toBeInTheDocument();
    expect(screen.getByTestId('extra-icon')).toBeInTheDocument();
  });
});

describe('ContextIcon - ubiquitous flag', () => {
  it('renders ubiquitous annotations when ubiquitous=true', () => {
    renderContextIcon(
      [baseAnnotation({ icon: 'mdi:fire', ubiquitous: true }), baseAnnotation({ icon: 'mdi:ice', ubiquitous: false })],
      { ubiquitous: true }
    );
    const icons = screen.getAllByTestId('context-icon');
    expect(icons).toHaveLength(1);
    expect(icons[0].getAttribute('data-icon')).toBe('mdi:fire');
  });

  it('ignores ubiquitous annotations when ubiquitous=false', () => {
    renderContextIcon(
      [baseAnnotation({ icon: 'mdi:fire', ubiquitous: true }), baseAnnotation({ icon: 'mdi:ice', ubiquitous: false })],
      { ubiquitous: false }
    );
    const icons = screen.getAllByTestId('context-icon');
    expect(icons).toHaveLength(1);
    expect(icons[0].getAttribute('data-icon')).toBe('mdi:ice');
  });
});

describe('ContextIcon - tooltip interactions', () => {
  beforeEach(() => {
    mockShowInfo.mockClear();
    mockCloseInfo.mockClear();
  });

  it('calls showInfo on mouse-over when tooltip is enabled', async () => {
    const user = userEvent.setup();
    renderContextIcon([baseAnnotation({ icon: 'mdi:fire' })]);
    const span = document.querySelector('span[style]');
    await user.hover(span);
    expect(mockShowInfo).toHaveBeenCalledWith('context', expect.anything(), selector, expect.anything());
  });

  it('calls closeInfo on mouse-leave when tooltip is enabled', async () => {
    const user = userEvent.setup();
    renderContextIcon([baseAnnotation({ icon: 'mdi:fire' })]);
    const span = document.querySelector('span[style]');
    await user.hover(span);
    await user.unhover(span);
    expect(mockCloseInfo).toHaveBeenCalledWith('context', selector);
  });

  it('does NOT call showInfo on mouse-over when disableTooltip=true', async () => {
    const user = userEvent.setup();
    renderContextIcon([baseAnnotation({ icon: 'mdi:fire' })], { disableTooltip: true });
    const span = document.querySelector('span[style]');
    await user.hover(span);
    expect(mockShowInfo).not.toHaveBeenCalled();
  });

  it('does NOT trigger closeInfo on mouse-leave when disableTooltip=true', async () => {
    const user = userEvent.setup();
    renderContextIcon([baseAnnotation({ icon: 'mdi:fire' })], { disableTooltip: true });
    const span = document.querySelector('span[style]');
    await user.hover(span);
    await user.unhover(span);
    // The component calls closeInfo once on mount (to dismiss any open tooltip). The
    // onMouseLeave handler is undefined when disableTooltip=true, so no second call should occur.
    expect(mockCloseInfo).toHaveBeenCalledOnce();
  });
});
