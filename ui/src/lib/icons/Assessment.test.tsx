import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Annotation } from 'lib/types/lookup';
import { createContext } from 'use-context-selector';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AssessmentIcon from './Assessment';

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

// Render Icon as a plain <span data-testid="…"> so we can assert which icon is shown
vi.mock('@iconify/react', () => ({
  Icon: ({ icon, color, ...rest }: { icon: string; color?: string; [key: string]: unknown }) => (
    <span id="assessment-icon" data-icon={icon} data-color={color ?? ''} {...rest} />
  )
}));

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

const BAD_ASSESSMENTS = ['trivial', 'recon', 'attempt', 'compromise', 'mitigated'] as const;
const GOOD_ASSESSMENTS = ['ambiguous', 'security', 'development', 'false-positive', 'legitimate'] as const;

const BAD_ICON = 'healthicons:hazardous';
const GOOD_ICON = 'fluent-mdl2:ribbon-solid';

const baseAnnotation = (value: string, quantity = 1, ubiquitous = false): Annotation => ({
  type: 'assessment',
  value,
  quantity,
  ubiquitous,
  confidence: 1,
  summary: value,
  analytic: `analytic-${value}`
});

const selector = { type: 'ip', value: '1.2.3.4' };

function renderAssessmentIcon(
  annotations: Annotation[],
  { counters = false, disableTooltip = false, ubiquitous = false } = {}
) {
  return render(
    <AssessmentIcon
      annotations={annotations}
      value={selector}
      counters={counters}
      disableTooltip={disableTooltip}
      ubiquitous={ubiquitous}
    />
  );
}

// Returns the data-icon of the primary (first rendered) icon
function primaryIconName() {
  const icons = screen.getAllByTestId('assessment-icon');
  return icons[0].getAttribute('data-icon');
}

// ------------------------------------------------------------------
// Tests
// ------------------------------------------------------------------

describe('AssessmentIcon - renders nothing when no assessment annotations', () => {
  it('returns null for an empty annotation list', () => {
    const { container } = renderAssessmentIcon([]);
    expect(container).toBeEmptyDOMElement();
  });

  it('returns null when annotations contain only non-assessment types', () => {
    const { container } = renderAssessmentIcon([{ ...baseAnnotation('compromise'), type: 'opinion' }]);
    expect(container).toBeEmptyDOMElement();
  });

  it('returns null when annotations have no matching ubiquitous flag', () => {
    // component defaults to ubiquitous=false; these annotations are ubiquitous=true
    const { container } = renderAssessmentIcon([baseAnnotation('compromise', 1, true)]);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('AssessmentIcon - renders with a single assessment', () => {
  it.each(BAD_ASSESSMENTS)('shows the hazardous icon for bad assessment "%s"', assessment => {
    renderAssessmentIcon([baseAnnotation(assessment)]);
    expect(primaryIconName()).toBe(BAD_ICON);
  });

  it.each(GOOD_ASSESSMENTS)('shows the ribbon icon for good assessment "%s"', assessment => {
    renderAssessmentIcon([baseAnnotation(assessment)]);
    expect(primaryIconName()).toBe(GOOD_ICON);
  });
});

describe('AssessmentIcon - higher-count assessment wins', () => {
  it('shows hazardous icon when bad assessment count exceeds good assessment count', () => {
    renderAssessmentIcon([baseAnnotation('compromise', 5), baseAnnotation('legitimate', 2)]);
    expect(primaryIconName()).toBe(BAD_ICON);
  });

  it('shows ribbon icon when good assessment count exceeds bad assessment count', () => {
    renderAssessmentIcon([baseAnnotation('legitimate', 5), baseAnnotation('trivial', 2)]);
    expect(primaryIconName()).toBe(GOOD_ICON);
  });

  it('quantity sums within same assessment value before comparison', () => {
    // Two 'legitimate' annotations each with quantity 3 → total 6; one 'compromise' with quantity 4
    // 'legitimate' (good) wins on count (6 vs 4)
    renderAssessmentIcon([
      baseAnnotation('legitimate', 3),
      baseAnnotation('legitimate', 3),
      baseAnnotation('compromise', 4)
    ]);
    expect(primaryIconName()).toBe(GOOD_ICON);
  });
});

describe('AssessmentIcon - ubiquitous flag', () => {
  it('renders the ubiquitous annotation when ubiquitous=true', () => {
    renderAssessmentIcon([baseAnnotation('compromise', 1, true), baseAnnotation('legitimate', 1, false)], {
      ubiquitous: true
    });
    expect(primaryIconName()).toBe(BAD_ICON);
  });

  it('ignores ubiquitous annotations when ubiquitous=false', () => {
    renderAssessmentIcon([baseAnnotation('compromise', 1, true), baseAnnotation('legitimate', 1, false)], {
      ubiquitous: false
    });
    expect(primaryIconName()).toBe(GOOD_ICON);
  });
});

describe('AssessmentIcon - tooltip interactions', () => {
  beforeEach(() => {
    mockShowInfo.mockClear();
    mockCloseInfo.mockClear();
  });

  it('calls showInfo on mouse-over when tooltip is enabled (bad assessment)', async () => {
    const user = userEvent.setup();
    renderAssessmentIcon([baseAnnotation('compromise')]);
    const span = document.querySelector('span[style]');
    await user.hover(span);
    expect(mockShowInfo).toHaveBeenCalledWith('assessment', expect.anything(), selector, expect.anything());
  });

  it('calls showInfo on mouse-over when tooltip is enabled (good assessment)', async () => {
    const user = userEvent.setup();
    renderAssessmentIcon([baseAnnotation('legitimate')]);
    const span = document.querySelector('span[style]');
    await user.hover(span);
    expect(mockShowInfo).toHaveBeenCalledWith('assessment', expect.anything(), selector, expect.anything());
  });

  it('calls closeInfo on mouse-leave when tooltip is enabled', async () => {
    const user = userEvent.setup();
    renderAssessmentIcon([baseAnnotation('compromise')]);
    const span = document.querySelector('span[style]');
    await user.hover(span);
    await user.unhover(span);
    expect(mockCloseInfo).toHaveBeenCalledWith('assessment', selector);
  });

  it('does NOT call showInfo on mouse-over when disableTooltip=true', async () => {
    const user = userEvent.setup();
    renderAssessmentIcon([baseAnnotation('compromise')], { disableTooltip: true });
    const span = document.querySelector('span[style]');
    await user.hover(span);
    expect(mockShowInfo).not.toHaveBeenCalled();
  });

  it('does NOT call closeInfo on mouse-leave when disableTooltip=true', async () => {
    const user = userEvent.setup();
    renderAssessmentIcon([baseAnnotation('compromise')], { disableTooltip: true });
    const span = document.querySelector('span[style]');
    await user.hover(span);
    await user.unhover(span);
    expect(mockCloseInfo).not.toHaveBeenCalled();
  });
});
