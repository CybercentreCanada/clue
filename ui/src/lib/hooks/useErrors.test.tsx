import { act, render } from '@testing-library/react';
import buildDatabase from 'lib/database';
import { v4 as uuid } from 'uuid';
import { ClueConfigProvider } from './ClueConfigProvider';
import { ClueDatabaseProvider } from './ClueDatabaseContext';
import { ClueEnrichProvider } from './ClueEnrichContext';
import useErrors from './useErrors';

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
const TestComponent = () => {
  const errors = useErrors('value');

  return (
    <div id="wrapper">
      {errors.map(_error => (
        <div id={_error.source} key={_error.source}>
          {_error.message}
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
      annotations: [],
      error: 'error_message'
    });
  });

  // Verify that the annotation is displayed in the component
  const error = result.getByTestId('example');

  expect(error.textContent).toBe('error_message');
});
