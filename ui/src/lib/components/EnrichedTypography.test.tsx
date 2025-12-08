import { render, waitFor } from '@testing-library/react';
import userEvent, { UserEvent } from '@testing-library/user-event';
import { createContext as reactCreateContext } from 'react';
import { createContext } from 'use-context-selector';
import { verifyExistence, verifyText } from '../../tests/test-utils';
import EnrichedTypography from './EnrichedTypography';

const database = await vi.hoisted(async () =>
  (await import('lib/database')).default({ devMode: false, storageType: 'memory' })
);

const mockQueueEnrich = vi.hoisted(() => vi.fn());
const mockShowInfo = vi.hoisted(() => vi.fn());

vi.mock('lib/hooks/ClueComponentContext', () => ({
  ClueComponentContext: createContext({
    i18next: { t: key => key }
  })
}));

vi.mock('lib/hooks/ClueEnrichContext', () => ({
  ClueEnrichContext: createContext({
    defaultClassification: 'example',
    ready: true,
    availableSources: ['example1'],
    queueEnrich: mockQueueEnrich
  })
}));

vi.mock('lib/hooks/ClueDatabaseContext', () => ({
  ClueDatabaseContext: reactCreateContext(database)
}));

vi.mock('lib/hooks/CluePopupContext', () => ({
  CluePopupContext: createContext({
    showInfo: mockShowInfo,
    closeInfo: vi.fn()
  })
}));

vi.mock('lib/hooks/ClueActionContext', () => ({
  ClueActionContext: createContext({
    getActionResults: vi.fn()
  })
}));

describe('Rendering', () => {
  it('should, with no children text, display the provided value', async () => {
    const type = 'ip';
    const value = '127.0.0.1';

    render(<EnrichedTypography value={value} type={type} />);

    verifyText(`enriched-${type}-value`, value);
  });

  it('should, with children, display the child and not the value', async () => {
    const type = 'ip';
    const value = '127.0.0.1';

    render(
      <EnrichedTypography value={value} type={type}>
        <span id="hello-world">hello world</span>
      </EnrichedTypography>
    );

    verifyExistence(`enriched-${type}-value`, false);
    verifyText(`hello-world`, 'hello world');
  });
});

describe('Functionality', () => {
  let user: UserEvent;
  beforeEach(async () => {
    mockQueueEnrich.mockClear();
    user = userEvent.setup();
  });

  it('should trigger enrichment when rendered', async () => {
    expect(mockQueueEnrich).not.toBeCalled();

    const type = 'ipv4';
    const value = '127.0.0.1';

    render(<EnrichedTypography value={value} type={type} />);

    await waitFor(() => {
      expect(mockQueueEnrich).toHaveBeenCalledOnce();
    });
  });

  it('should trigger a modal opening if clicked', async () => {
    const type = 'ipv4';
    const value = '127.0.0.1';

    const { container } = render(<EnrichedTypography value={value} type={type} />);

    const typography = container.querySelector('.enriched-typography');
    user.click(typography);

    await waitFor(() => {
      expect(mockShowInfo).toBeCalledWith('details', typography, { classification: 'example', type, value }, {});
    });
  });
});
