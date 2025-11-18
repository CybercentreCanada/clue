# Testing Clue in another application

## The Problem

When integrating Clue-UI into another application and writing unit tests with Jest and React Testing Library, you may encounter test failures due to how the library manages its internal state and database connections.

### Root Cause

The primary issue stems from **continually re-rendering the entire ClueProvider** during test execution. While this approach works fine for most stateless React components and functions, it creates significant problems when working with **RxDB** (Reactive Database), which is used internally by Clue-UI for data management.

### Why RxDB Struggles with Re-renders

RxDB maintains persistent database connections and reactive subscriptions. When the ClueProvider is recreated for each test (a common pattern in React Testing Library), several issues occur:

1. **Database Connection Conflicts**: Multiple database instances attempting to access the same storage can lead to locking issues
2. **Memory Leaks**: Previous database instances may not be properly cleaned up before new ones are created
3. **Subscription Management**: RxDB's reactive subscriptions can persist across test boundaries, causing unexpected side effects
4. **Async Timing Issues**: Database initialization is asynchronous, and rapid recreation can lead to race conditions

### Common Test Failure Patterns

You might see errors like:

- Database connection timeouts
- "Database already exists" errors
- Tests that pass individually but fail when run in a suite
- Intermittent failures that are difficult to reproduce
- Memory usage that continues to grow across test runs

## The Solution

To mitigate this, it's best to create a **static instance of the database** and pass the same instance between tests/renders. This ensures consistent state management and prevents the database connection issues described above.

As an example, taken from [`enrich.test.tsx`](../src/lib/hooks/enrich.test.tsx):

```tsx
// Initialize test database
const database = await buildDatabase({ devMode: false, storageType: 'memory' });

// Test wrapper component that provides the enrichment context
const Wrapper = ({ children }) => {
  return (
    <ClueProvider
      ready
      database={database}
      getToken={getToken}
      onNetworkCall={onNetworkCall}
      pickSources={pickSources}
      chunkSize={ENRICH_CHUNK_SIZE}
      debugLogging={!!process.env.ENABLE_DEBUG_LOGGNIG}
      config={MOCK_RESPONSES['/api/v1/configs']}
      skipConfigCall
    >
      {children}
    </ClueProvider>
  );
};

describe('enrich functionality', () => {
  it('should return the expected list of available sources', async () => {
    const { result } = await act(async () => {
      return renderHook(() => useClueEnrichSelector(ctx => ctx.availableSources), { wrapper: Wrapper });
    });

    expect(result.current).toEqual(['example', 'potato']);
  });
});
```
