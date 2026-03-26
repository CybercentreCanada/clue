# Clue API Release Notes

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
