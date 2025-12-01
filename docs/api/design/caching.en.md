# Caching in Clue

Clue implements a multi-layered caching architecture to optimize performance and reduce redundant enrichment requests.
The caching system operates at both the client-side (UI) and server-side (API/Plugins) levels, providing efficient data
storage and retrieval across different components.

## Overview

The caching architecture consists of two main layers:

1. **Client-side Caching**: Browser-based storage for UI data persistence.
2. **Plugin-side Caching**: Server-side caching (Redis or Local) within individual plugins.

Cache Bypass Controls allow users to force fresh data retrieval when needed.

## User Guide: Caching FAQ

This section addresses common questions for analysts and users regarding data persistence and freshness.

### Is the data saved anywhere?

**No.** Clue uses **session storage**, which means your enrichment data persists only as long as your browser tab is open.
**Warning:** If you close your tab or window, all your current enrichment results will be lost.

### How long does the data stay "fresh"?

By default, plugins cache results for **5 minutes**. If you search for the same indicator within that window, you will see the cached result. After 5 minutes, Clue will automatically fetch new data from the source.

### How do I bypass the cache/get new data immediately?

If you suspect the data has changed (e.g., an IP reputation update), you can force a refresh:

1. In the Clue UI Homepage, look for the **"Skip Plugins' Cache"** checkbox option.
2. Enable this option before running your enrichment.
3. This forces Clue to ignore any cached results and fetch live data.

Alternatively, in an application with the clue UI integrated, you can force refreshing from specific plugins using the
enrich button:

1. Click on the selector you wish to refresh
2. Click the "Enrich" button a tthe top right of the popover
3. Select the source you wish to re-enrich from.
4. This forces that plugin to ignore any cached results and fetch live data.

### Why is it faster the second time?

When you view a result you've already enriched in your current session, it loads instantly because it is stored in your browser's local cache (Client-side caching).

## Client-side Caching (UI)

The Clue UI uses a reactive, client-side database (RxDB) to store your data while you work. This allows for real-time updates and offline capabilities.

### Session Storage (Data Persistence)

**Important:** The UI uses **session storage**, which means:

* **Session-scoped persistence**: Data persists only for the browser session.
* **Automatic cleanup**: Data is cleared when the browser tab/window is closed.
* **Cross-tab isolation**: Each browser tab maintains its own cache.

<details>
<summary>Technical Implementation: RxDB Configuration</summary>

The UI database is configured to use session storage as its backend.

```typescript
// Storage configuration with session storage backend
storage: wrappedKeyCompressionStorage({
  storage: wrappedValidateAjvStorage({
    storage: getRxStorageLocalstorage({ localStorage: sessionStorage })
  })
})
```

</details>

### Data Collections

The database manages two main types of data:

1. **Selectors**: Stores enrichment results, annotations, and classification data.
2. **Status**: Tracks the state of requests (`pending`, `in-progress`, `complete`) to manage queues and prevent duplicates.

<details>
<summary>Technical Implementation: Collections</summary>

#### Selectors Collection

* Schema: `ui/src/lib/database/selector.schema.json`
* Indexed by type, value, and classification for efficient querying
* Automatically manages data compression and validation

#### Status Collection

* Schema: `ui/src/lib/database/status.schema.json`
* Enables queue management for bulk enrichment operations
* Prevents duplicate requests by checking existing status records

</details>

### Enrichment Workflow

When you request enrichment data, the system follows a structured workflow to prevent duplicate requests and manage
data efficiently:

1. **Status Check**: The system first checks if the enrichment is already in progress or completed
2. **Request Queuing**: New requests are queued with appropriate status tracking
3. **Data Storage**: Results are automatically stored in the local database for future use

<details>
<summary>Technical Implementation</summary>

```typescript
/**
 * ui/src/lib/hooks/ClueEnrichContext
 */

// 1. Check existing status to prevent duplicates
let statusRecord = await database.status
  .findOne({ selector: { type, value, classification } })
  .exec();

// 2. Create or update status record
if (!statusRecord) {
  statusRecord = await database.status.insert({
    id: uuid(),
    type, value, classification,
    status: 'pending'
  });
}

// 3. Queue enrichment and store results
const enrichmentResult = await lookup.enrich.post([selector], sources, options);
await _addEntries(Object.values(enrichData));
```

</details>

### Queue Management

The client implements intelligent queue management to optimize performance:

* **Debounced Processing**: Enrichment requests are batched and processed with a 200ms debounce
* **Chunked Requests**: Large batches are split into configurable chunks (default: 15 selectors)
* **Concurrent Limits**: Maximum concurrent requests are controlled (default: 4 requests)
* **Manual Retry**: Failed enrichments can be retried on user request through the retry functionality

## Plugin-side Caching

Plugins use server-side caching to improve response times. This means if you or a colleague searches for the same indicator, the system can return the previous result instead of querying the external service again.

### Cache Types and Consistency

The system can be configured in two ways, which affects how data is shared between users:

1. **Redis Caching (Shared)**: The cache is shared across the entire system. If you enrich an indicator, your colleague will see the cached result when they query the same indicator (note: there may be slight propagation delays in distributed systems).
2. **Local Memory Caching (Isolated)**: Each processing unit ("worker") has its own cache.

**Analyst Note (Troubleshooting):**
If you and a colleague see different results for the same indicator at the same time, your system might be using **Local Caching**. In this mode, you might hit a worker that has old data, while your colleague hits a worker with new data.

<details>
<summary>Technical Implementation: Cache Types</summary>

#### Redis Caching

Redis provides distributed caching that is shared across all plugin workers and pods in a Kubernetes cluster. In scalable
deployments with many workers, using a centralized cache like redis is preferred so workers can share cache information.
Conversely, the ease of simple cache systems on smaller deployments with only a single flask server running requires less
infrastructure and may be a better fit.

```python
# api/clue/cache/__init__.py
# Uses ExpiringHash for distributed caching
self.__redis_cache = ExpiringHash(cache_name, host=get_redis(), ttl=timeout)
```

#### Local Memory Caching

Local memory caching stores data within individual plugin workers. In Kubernetes deployments, each worker maintains its own independent cache.

```python
# Uses Flask-Caching with SimpleCache backend
self.__local_cache = FlaskCache(app, config={
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": timeout
})
```

</details>

### Cache Keys

The system ensures that different types of requests for the same indicator are cached separately. For example, a request asking for "raw data" will be cached separately from one that doesn't.

<details>
<summary>Technical Implementation: Key Generation</summary>

Cache keys are generated using SHA256 hashing of:

* Selector type and value
* Annotation inclusion settings
* Raw data inclusion settings
* Result limit parameters

```python
# api/clue/cache/__init__.py
def __generate_hash(self, type_name: str, value: str, params: Params) -> str:
    hash_data = sha256(type_name.encode())
    hash_data.update(value.encode())

    hash_data.update(str(params.annotate).encode())
    hash_data.update(str(params.raw).encode())
    hash_data.update(str(params.limit).encode())
    return hash_data.hexdigest()
```

</details>

## Cache Bypass Controls

Sometimes you need to ensure you are seeing the absolute latest data, ignoring any cached results.

### Using the UI (Skip Plugins' Cache)

To force a fresh lookup:

1. Locate the **"Skip Plugins' Cache"** option in the interface.
2. Enable it before submitting your request.

<details>
<summary>Technical Implementation: API & Client</summary>

#### API-level Cache Control

The API supports cache bypass through the `no_cache` parameter.

```python
# Query parameter parsing
no_cache = request.args.get("no_cache", "false").lower() in ("true", "1", "")
```

#### Client-side Cache Control

The UI sends this parameter when the option is selected.

```typescript
const options = {
  noCache: true,  // Bypass plugin caching
  force: true,    // Force new enrichment request
};
```

</details>

## Performance Considerations

### Client-side Optimizations

* **Reactive Updates**: RxDB provides real-time UI updates when new data arrives
* **Intelligent Batching**: Requests are automatically grouped to reduce API calls
* **Status Tracking**: Prevents duplicate requests for the same selector
* **Memory Management**: Session storage automatically cleans up on tab close
* **Key Compression**: RxDB uses key compression to reduce storage overhead

### Plugin-side Optimizations

* **Configurable TTL**: Cache timeout can be adjusted per plugin (default: 5 minutes)
* **Serialization**: Efficient JSON serialization with Pydantic models
* **Error Handling**: Graceful fallback when cache operations fail

## Cache Invalidation

### Automatic Invalidation

* **TTL Expiration**: Cache entries automatically expire after the configured timeout
* **Session End**: Client-side cache is cleared when browser session ends
* **Status Reset**: In-progress requests are cleared on application startup

### Manual Invalidation

* **Plugin Cache**: Individual cache entries can be deleted using `cache.delete()`
* **Client Cache**: Failed enrichments can be cleared and retried
* **API Bypass**: The `no_cache` parameter forces fresh data retrieval

## Configuration Examples

### Plugin Cache Configuration

Plugins can be configured to use either Redis (recommended for production) or local memory caching.

<details>
<summary>Configuration Examples</summary>

```python
# Redis caching with 10-minute TTL
plugin = CluePlugin(
    app_name="example-plugin",
    enable_cache="redis",
    cache_timeout=10 * 60
)

# Local memory caching
plugin = CluePlugin(
    app_name="example-plugin",
    enable_cache="local",
    local_cache_options={"CACHE_TYPE": "SimpleCache"}
)
```

</details>

### UI Database Configuration

The UI database can be configured for different environments and use cases.

<details>
<summary>Configuration Examples</summary>

```typescript
// Production: Session storage with compression
const config: DatabaseConfig = {
  storageType: 'session',
  devMode: false
};

// Testing: Memory storage without compression
const config: DatabaseConfig = {
  storageType: 'memory',
  devMode: true,
  testing: true
};
```

</details>
