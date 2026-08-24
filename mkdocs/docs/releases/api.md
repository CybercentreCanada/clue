# Clue API Release Notes

## `v1.6.0`

- **Source Exclusions for Enrichment** *(new feature)*: Enrichment requests can now exclude configured sources, with exclusions taking precedence over inclusions and support for per-selector source filters ([#81](https://github.com/CybercentreCanada/clue/pull/81)).
- **Fetcher Classification Validation** *(bugfix)*: Validated fetcher availability, request bodies, and classification access before sending selector data to external fetchers ([#85](https://github.com/CybercentreCanada/clue/pull/85)).
- **Replication Cache Improvements** *(bugfix)*: Improved replicated-result matching and expiry handling, and ensured `no_cache` enrichment invalidates stale replicated results before storing fresh ones ([#89](https://github.com/CybercentreCanada/clue/pull/89)).
- **MongoDB Authentication Source** *(improvement)*: Added configuration for selecting the authentication source when connecting to MongoDB.
- **Synchronized Replication Models** *(improvement)*: Updated synchronization models to support selector expiry data consistently between the API and UI.

## `v1.5.3`

- **Clue Plugin Dependency Improvements** *(bugfix)*: Fixed missing dependendencies in the clue plugin library.

## `v1.5.2`

- **Annotation Timestamp Validation** *(bugfix)*: Tightened `Annotation.timestamp` validation so ISO-formatted timestamp strings continue to parse correctly while invalid timestamp values now fail validation. Added unit test coverage for default timestamp generation, string parsing, and invalid input handling.

## `v1.5.1`

- **JWT Service Import Chain** *(bugfix)*: Fixed an issue where `jwt_service` pulled in a long chain of module imports through the security package, reducing import coupling and preventing related startup/runtime failures ([#83](https://github.com/CybercentreCanada/clue/pull/83)).

## `v1.5.0`

- **Data Replication API** *(new feature)*: Added authenticated pull, push, and server-sent event endpoints for synchronizing supported collections with RxDB clients ([#47](https://github.com/CybercentreCanada/clue/pull/47)).
- **Plugin Query Helpers** *(new feature)*: Added helpers that let plugins query other configured plugins ([#78](https://github.com/CybercentreCanada/clue/pull/78)).
- **Pending Action Output Validation** *(bugfix)*: Added validation for output returned by pending actions ([#80](https://github.com/CybercentreCanada/clue/pull/80)).
- **Documentation File Serving** *(bugfix)*: Fixed documentation file lookup and added the `CLUE_DOCUMENTATION_PATH` setting for configuring the documentation directory.
- **Pydantic Response Serialization** *(improvement)*: API response helpers now serialize Pydantic models consistently, including aliases and JSON-compatible values.
- **Dependency and CI Updates** *(technical update)*: Updated Python dependencies and expanded CI testing to Python 3.13.

## `v1.4.0`

- **Async Fetcher Results** *(new feature)*: Fetchers can now return results asynchronously for improved responsiveness on long-running lookups ([#35](https://github.com/CybercentreCanada/clue/pull/35)).
- **File Result Type** *(new feature)*: Actions and fetchers can now produce file results, enabling file-based output handling ([#38](https://github.com/CybercentreCanada/clue/pull/38)).
- **More Default Supported Types** *(new feature)*: Expanded the set of types supported by default.
- **Action Execution Context** *(new feature)*: Added context passing to action execution for richer runtime information.
- **Plugin Dashboard** *(bugfix)*: Fixed and improved the plugin dashboard ([#43](https://github.com/CybercentreCanada/clue/pull/43)).
- **Action Context Format** *(bugfix)*: Fixed the action context payload format to match what is sent by the UI ([#48](https://github.com/CybercentreCanada/clue/pull/48)).
- **Raw Data and Timestamps** *(bugfix)*: Fixed raw data handling and added timestamp support ([#41](https://github.com/CybercentreCanada/clue/pull/41)).
- **pip Dependency Updates** *(technical update)*: Updated pip group dependencies ([#34](https://github.com/CybercentreCanada/clue/pull/34), [#45](https://github.com/CybercentreCanada/clue/pull/45)).

## `v1.3.2`

- **Closed Selector Collection Guard** *(bugfix)*: Added a check to prevent queries against closed selector collections.
- **Closed Collection Enrichment Guard** *(bugfix)*: Added a check to skip enrichment queuing for closed collections.
- **libffi-dev Build Fix** *(bugfix)*: Fixed double-installation of `libffi-dev` during builds.

## `v1.3.0`

- **Extension Initialization Hooks** *(new feature)*: Added support for `init` module hooks to run custom logic on extension startup.
- **Custom Type Registration** *(new feature)*: Added `add_supported_type()` function for registering custom types with regex validation, namespace support, and case-insensitive matching.
- **Asynchronous Action Support** *(new feature)*: Actions can now run asynchronously with a new `/actions/<plugin_id>/<action_id>/status/<task_id>` status endpoint, an `async_result` flag, a `pending` outcome on `ActionResult`, and a new `ActionContextInformation` model.
- **TESTING Environment Variable** *(new feature)*: Added `TESTING` environment variable for cleaner test environment detection.
- **DISABLE_CACHE Environment Variable** *(new feature)*: Added `DISABLE_CACHE` environment variable to disable caching on demand.
- **Lowercase Selector Normalization** *(improvement)*: Selector values are now normalized to lowercase (except for the telemetry type) for consistent matching.
- **Type Count Logging** *(improvement)*: Added logging for the total number of configured types, including custom types.
- **Plugins Renamed to Extensions** *(improvement)*: Renamed "plugins" to "extensions" throughout the codebase. The `CLUE_PLUGIN_DIRECTORY` environment variable is deprecated in favour of `CLUE_EXTENSION_PATH` (backward compatible with a deprecation warning). Extension path now defaults to `/etc/clue/extensions`.
- **Error Handling in App Discovery** *(improvement)*: Enhanced app discovery with better error handling and configurable timeout support.
- **Cache Set Error Logging** *(bugfix)*: Fixed incorrect log message on cache set errors (was "Error on retrieval", now "Error on cache set").
- **Application Entry Point Migration** *(technical update)*: Migrated from `clue.patched` to `clue.app` as the application entry point.
- **HTTP Client Replacement** *(technical update)*: Replaced `geventhttpclient` with the `requests` library for HTTP operations.
- **French README** *(technical update)*: Added French README translation.
- **CI/CD Branch Trigger** *(technical update)*: Updated CI/CD workflow to trigger on the `develop` branch.

## `v0.13.0`

- **Plugin Documentation** *(new feature)*: Added plugin documentation pages.
- **IPv4/IPv6 Type Refactor** *(improvement)*: Refactored the generic `ip` type into separate `ipv4` and `ipv6` types.
- **Domain Regex Fix** *(bugfix)*: Fixed a regex that prevented matching double-hyphenated domains such as `doublehypenated--domains.com`.
- **Empty Selector Actions** *(new feature)*: Added `accept_empty` flag allowing actions to execute with no selectors provided.
- **Expired Token Detection** *(bugfix)*: Added a check to reject expired tokens from the token cache rather than using them.
- **Enrichment Parameter Validation** *(improvement)*: Added improved validation of enrichment parameters.
- **Classification-Based Enrichment Fix** *(bugfix)*: Fixed enrichments returning no entries when a single entry exceeded the maximum allowed classification.
