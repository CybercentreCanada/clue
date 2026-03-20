import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Annotation } from 'lib/types/lookup';
import { createContext } from 'use-context-selector';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import OpinionIcon from './Opinion';

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

// Render Icon as a plain <span data-icon="…"> so we can assert which icon is shown
vi.mock('@iconify/react', () => ({
  Icon: ({ icon, color, ...rest }: { icon: string; color?: string; [key: string]: unknown }) => (
    <span id="opinion-icon" data-icon={icon} data-color={color ?? ''} {...rest} />
  )
}));

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

const baseAnnotation = (value: string, quantity = 1, ubiquitous = false): Annotation => ({
  type: 'opinion',
  value,
  quantity,
  ubiquitous,
  confidence: 1,
  summary: value
});

const selector = { type: 'ip', value: '1.2.3.4' };

function renderOpinionIcon(
  annotations: Annotation[],
  { counters = false, disableTooltip = false, ubiquitous = false } = {}
) {
  return render(
    <OpinionIcon
      annotations={annotations}
      value={selector}
      counters={counters}
      disableTooltip={disableTooltip}
      ubiquitous={ubiquitous}
    />
  );
}

// ------------------------------------------------------------------
// Helper: gets the primary (outermost) icon's `data-icon` attribute
// ------------------------------------------------------------------
function primaryIconName() {
  const icons = screen.getAllByTestId('opinion-icon');
  return icons[0].getAttribute('data-icon');
}

// ------------------------------------------------------------------
// Tests
// ------------------------------------------------------------------

describe('OpinionIcon - renders nothing when no opinion annotations', () => {
  it('returns null for an empty annotation list', () => {
    const { container } = renderOpinionIcon([]);
    expect(container).toBeEmptyDOMElement();
  });

  it('returns null when annotations contain only non-opinion types', () => {
    const { container } = renderOpinionIcon([{ ...baseAnnotation('benign'), type: 'context' }]);
    expect(container).toBeEmptyDOMElement();
  });

  it('returns null when annotations have no matching ubiquitous flag', () => {
    // component defaults to ubiquitous=false; these annotations are ubiquitous=true
    const { container } = renderOpinionIcon([baseAnnotation('malicious', 1, true)]);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('OpinionIcon - renders with a single opinion', () => {
  it.each([
    ['benign', 'mdi:shield-check'],
    ['suspicious', 'mdi:warning-outline'],
    ['obscure', 'bi:eye-slash-fill'],
    ['malicious', 'mdi:warning-decagram']
  ])('shows the correct icon for opinion "%s"', (opinion, expectedIcon) => {
    renderOpinionIcon([baseAnnotation(opinion)]);
    expect(primaryIconName()).toBe(expectedIcon);
  });
});

describe('OpinionIcon - higher-count opinion wins', () => {
  it('shows malicious icon when malicious count > suspicious count', () => {
    renderOpinionIcon([baseAnnotation('malicious', 5), baseAnnotation('suspicious', 3)]);
    expect(primaryIconName()).toBe('mdi:warning-decagram');
  });

  it('shows suspicious icon when suspicious count > benign count', () => {
    renderOpinionIcon([baseAnnotation('suspicious', 4), baseAnnotation('benign', 1)]);
    expect(primaryIconName()).toBe('mdi:warning-outline');
  });
});

describe('OpinionIcon - tie-breaking by severity', () => {
  it('prefers malicious over suspicious on a count tie', () => {
    renderOpinionIcon([baseAnnotation('suspicious', 2), baseAnnotation('malicious', 2)]);
    expect(primaryIconName()).toBe('mdi:warning-decagram');
  });

  it('prefers malicious over obscure on a count tie', () => {
    renderOpinionIcon([baseAnnotation('obscure', 3), baseAnnotation('malicious', 3)]);
    expect(primaryIconName()).toBe('mdi:warning-decagram');
  });

  it('prefers malicious over benign on a count tie', () => {
    renderOpinionIcon([baseAnnotation('benign', 1), baseAnnotation('malicious', 1)]);
    expect(primaryIconName()).toBe('mdi:warning-decagram');
  });

  it('prefers suspicious over obscure on a count tie', () => {
    renderOpinionIcon([baseAnnotation('obscure', 2), baseAnnotation('suspicious', 2)]);
    expect(primaryIconName()).toBe('mdi:warning-outline');
  });

  it('prefers suspicious over benign on a count tie', () => {
    renderOpinionIcon([baseAnnotation('benign', 2), baseAnnotation('suspicious', 2)]);
    expect(primaryIconName()).toBe('mdi:warning-outline');
  });

  it('prefers obscure over benign on a count tie', () => {
    renderOpinionIcon([baseAnnotation('benign', 4), baseAnnotation('obscure', 4)]);
    expect(primaryIconName()).toBe('bi:eye-slash-fill');
  });

  it('three-way tie: malicious wins over suspicious and obscure', () => {
    renderOpinionIcon([baseAnnotation('obscure', 2), baseAnnotation('suspicious', 2), baseAnnotation('malicious', 2)]);
    expect(primaryIconName()).toBe('mdi:warning-decagram');
  });

  it('four-way tie: malicious wins', () => {
    renderOpinionIcon([
      baseAnnotation('benign', 1),
      baseAnnotation('obscure', 1),
      baseAnnotation('suspicious', 1),
      baseAnnotation('malicious', 1)
    ]);
    expect(primaryIconName()).toBe('mdi:warning-decagram');
  });

  it('quantity sums within same opinion type before comparison', () => {
    // Two benign annotations each with quantity 3 → total 6; one malicious with quantity 4
    // benign wins on count (6 vs 4), not on severity
    renderOpinionIcon([baseAnnotation('benign', 3), baseAnnotation('benign', 3), baseAnnotation('malicious', 4)]);
    expect(primaryIconName()).toBe('mdi:shield-check');
  });
});

describe('OpinionIcon - ubiquitous flag', () => {
  it('renders the ubiquitous annotation when ubiquitous=true', () => {
    renderOpinionIcon([baseAnnotation('malicious', 1, true), baseAnnotation('benign', 1, false)], {
      ubiquitous: true
    });
    expect(primaryIconName()).toBe('mdi:warning-decagram');
  });

  it('ignores ubiquitous annotations when ubiquitous=false', () => {
    renderOpinionIcon([baseAnnotation('malicious', 1, true), baseAnnotation('benign', 1, false)], {
      ubiquitous: false
    });
    expect(primaryIconName()).toBe('mdi:shield-check');
  });
});

describe('OpinionIcon - tooltip interactions', () => {
  beforeEach(() => {
    mockShowInfo.mockClear();
    mockCloseInfo.mockClear();
  });

  it('calls showInfo on mouse-over when tooltip is enabled', async () => {
    const user = userEvent.setup();
    renderOpinionIcon([baseAnnotation('malicious')]);
    const span = screen.getByStyle ? screen.getByRole('generic') : document.querySelector('span[style]');
    await user.hover(span);
    expect(mockShowInfo).toHaveBeenCalledWith('opinion', expect.anything(), selector, expect.anything());
  });

  it('calls closeInfo on mouse-leave when tooltip is enabled', async () => {
    const user = userEvent.setup();
    renderOpinionIcon([baseAnnotation('malicious')]);
    const span = document.querySelector('span[style]');
    await user.hover(span);
    await user.unhover(span);
    expect(mockCloseInfo).toHaveBeenCalledWith('opinion', selector);
  });

  it('does NOT call showInfo on mouse-over when disableTooltip=true', async () => {
    const user = userEvent.setup();
    renderOpinionIcon([baseAnnotation('malicious')], { disableTooltip: true });
    const span = document.querySelector('span[style]');
    await user.hover(span);
    expect(mockShowInfo).not.toHaveBeenCalled();
  });

  it('does NOT call closeInfo on mouse-leave when disableTooltip=true', async () => {
    const user = userEvent.setup();
    renderOpinionIcon([baseAnnotation('malicious')], { disableTooltip: true });
    const span = document.querySelector('span[style]');
    await user.hover(span);
    await user.unhover(span);

    // The component calls closeInfo('opinion', ...) on mount when disableTooltip=true to
    // dismiss any existing tooltip — that is intentional. What must NOT happen is the
    // onMouseLeave handler firing, which would call closeInfo again.
    expect(mockCloseInfo).toHaveBeenCalledOnce();
  });
});
