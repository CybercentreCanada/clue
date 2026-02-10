# Clue API Release Notes

## `v1.3.0`

### Features
- Added extension initialization support via `init` module hooks
- Added custom type registration system with `add_supported_type()` function
  - Supports custom types with regex validation
  - Supports namespaced types
  - Supports case-insensitive type handling
- Added asynchronous action support
  - New `/actions/<plugin_id>/<action_id>/status/<task_id>` endpoint for checking action status
  - Added `async_result` flag for actions
  - Added "pending" outcome status for `ActionResult`
  - Added `ActionContextInformation` model for contextual action execution
- Added `TESTING` environment variable for improved test environment detection
- Added `DISABLE_CACHE` environment variable to disable caching when needed
- Normalized selector values to lowercase (except telemetry type) for consistent matching
- Added logging for number of configured types including custom types

### Improvements
- Improved error logging in cache operations
- Enhanced app discovery with better error handling and timeout support
- Added timeout parameter to discovery HTTP requests
- Renamed "plugins" to "extensions" throughout the codebase
  - Environment variable `CLUE_PLUGIN_DIRECTORY` deprecated in favor of `CLUE_EXTENSION_PATH` (backward compatible with deprecation warning)
  - Extension path now defaults to `/etc/clue/extensions`
- Migrated from `clue.patched` to `clue.app` module for application entry point
- Replaced `geventhttpclient` with `requests` library for HTTP operations

### Bug Fixes
- Fixed cache error logging message (was "Error on retrieval", now correctly "Error on cache set")
- Improved test environment detection using `TESTING` flag

### Documentation
- Added French README translation
- Updated CI/CD workflow to trigger on `develop` branch

## `v0.13.0`

- Added plugin documentation
- Refactored `ip` type to `ipv4` and `ipv6`
- Fixed bug in domain regex that would not match against `doublehypenated--domains.com`
- Added ability for actions to accept no selectors (`accept_empty`)
- Added check to catch expired tokens in token cache instead of using them anyway
- Added improved validation of enrichment parameters
- Added fix for enrichments not returning any entries if a single entry is too high of a classification
