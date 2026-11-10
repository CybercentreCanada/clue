import { act, render } from '@testing-library/react';
import buildDatabase from 'lib/database';
import { v4 as uuid } from 'uuid';
import { ClueConfigProvider } from './ClueConfigProvider';
import { ClueDatabaseProvider } from './ClueDatabaseContext';
import { ClueEnrichProvider } from './ClueEnrichContext';
import { default as useAnnotations } from './useAnnotations';

// Mocking API calls for lookup types and type detection
vi.mock('api/lookup', () => {
  return {
    types: {
      get: () =>
        Promise.resolve({
          ip: ['example']
        })
    },
    types_detection: {
      get: () =>
        Promise.resolve({
          ip: /.+/
        })
    }
  };
});

// Test component to use the useAnnotations hook
const TestComponent = ({ skipEnrichment = true }) => {
  const [annotations, loading] = useAnnotations('ip', 'value', 'TLP:WHITE', { skipEnrichment });

  return (
    <div id="wrapper">
      {loading && <p id="loading">loading</p>}
      {annotations.map(_annotation => (
        <div id={_annotation.type as string} key={_annotation.type}>
          {_annotation.value}
        </div>
      ))}
    </div>
  );
};

// Main test for the useAnnotations hook
// This test verifies the loading state, enrichment process, and annotation retrieval
test('useAnnotations', async () => {
  const database = await buildDatabase({ devMode: false, storageType: 'memory' });

  // Render the TestComponent within the required providers
  const result = render(
    <ClueConfigProvider config={{ configuration: {}, c12nDef: {} } as any}>
      <ClueDatabaseProvider database={database}>
        <ClueEnrichProvider skipConfigCall ready>
          <TestComponent />
        </ClueEnrichProvider>
      </ClueDatabaseProvider>
    </ClueConfigProvider>
  );

  // By default, the component should be empty
  expect(result.getByTestId('wrapper')).toBeEmptyDOMElement();

  // Insert a status entry into the database and verify the loading state
  const statusId = uuid();
  await act(async () => {
    await database.status.insert({
      id: statusId,
      type: 'ip',
      value: 'value',
      classification: 'TLP:WHITE',
      status: 'in-progress'
    });
  });

  // Verify that the loading indicator is displayed
  expect(result.getByTestId('loading').textContent).toBe('loading');

  // Update the status to complete and verify the loading indicator is removed
  await act(async () => {
    await database.status.findOne(statusId).patch({ status: 'complete' });
  });

  expect(result.queryByTestId('loading')).toBeNull();

  // Insert a selector entry with annotations into the database
  await act(async () => {
    await database.selectors.insert({
      id: uuid(),
      type: 'ip',
      value: 'value',
      source: 'example',
      classification: 'TLP:WHITE',
      count: 2,
      latency: 100,
      annotations: [
        {
          confidence: 0,
          type: 'context' as const,
          value: 'value',
          summary: '',
          quantity: 0,
          ubiquitous: false
        }
      ]
    });
  });

  // Verify that the annotation is displayed in the component
  const annotation = result.getByTestId('context');

  expect(annotation.textContent).toBe('value');
});
