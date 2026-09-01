# Clue UI Release Notes

## `1.4.1`

- **Classification Chip Safety** *(bugfix)*: Prevented classification chips from accessing level data when a classification cannot be parsed, preserving default styling instead of causing a runtime error.
- **Silent Plugin Loading** *(improvement)*: Added a `silent` option to `ClueUIPluginProvider` to suppress plugin author installation logs for applications that manage plugin logging themselves.

## `1.4.0`

- **Standalone UI Authentication** *(bugfix)*: Propagated the stored application token to database replication, enrichment requests, and UI plugins so standalone deployments authenticate correctly.
- **Application Links** *(bugfix)*: Fixed links in annotation detail popovers so they open normally.
- **Replication Readiness** *(bugfix)*: Improved replication lifecycle handling and readiness tracking so the UI becomes ready reliably after selector synchronization.
- **Synchronized Selector Model** *(improvement)*: Added selector expiry support to the local database schema to keep the UI model aligned with the API.
- **Enrichment Cleanup** *(bugfix)*: Pending enrichment work is now cancelled during teardown to prevent stale queued operations.

## `1.3.0`

- **Clue UI Plugins** *(new feature)*: Added support for UI plugins, including a route for testing plugin integrations ([#73](https://github.com/CybercentreCanada/clue/pull/73), [#79](https://github.com/CybercentreCanada/clue/pull/79)).
- **Data Replication** *(new feature)*: Added replication and local storage support for synchronizing Clue data ([#47](https://github.com/CybercentreCanada/clue/pull/47)).
- **Action Failure Handling** *(bugfix)*: Actions now stop executing after a failure instead of continuing unexpectedly ([#62](https://github.com/CybercentreCanada/clue/pull/62)).
- **Pending Request Handling** *(bugfix)*: Fixed duplicate pending requests ([#74](https://github.com/CybercentreCanada/clue/pull/74)).
- **Dashboard and Database Stability** *(bugfix)*: Fixed dashboard display issues and database warnings ([#69](https://github.com/CybercentreCanada/clue/pull/69), [#71](https://github.com/CybercentreCanada/clue/pull/71)).
- **Telemetry Value Handling** *(bugfix)*: Corrected handling of telemetry selector values.
- **Query Links and Email Layout** *(improvement)*: Query links now target their associated verdict documents, and email rendering no longer overflows ([#60](https://github.com/CybercentreCanada/clue/pull/60)).
- **Dependency Updates** *(technical update)*: Updated UI dependencies, including Vite and picomatch.

## `1.2.8`

- **Clue Chip Height Bug** *(bugfix)*: Fixed a bug where the EnrichedChip would be forced to 40px if the size was unset.

## `1.2.7`

- **Status Collection Null Safety** *(bugfix)*: Added optional chaining and null guards for `database.status` in the enrich context to prevent errors when the status collection is unavailable or closed.
- **Queued Enrichment Fixes** *(bugfix)*: `queueEnrich` now returns early when the status collection is null or closed, preventing an unhandled promise rejection from calling `findOne` on a closed RxDB collection.

## `v1.2.6`

- **onUpdate handler for actions** *(bugfix)*: The `onUpdate` callback was not included in the action options when executing the action from the form.

## `v1.2.5`

- **onUpdate handler for actions** *(feature)*: Add `onUpdate` callback function to the executeAction hook for monitoring the progress of long-running actions.

## `v1.2.4`

- **Async Action `onComplete` Callback** *(bugfix)*: The `onComplete` callback passed to `executeAction` is now correctly deferred for async (`pending`) actions and is called once the action resolves via polling, rather than being silently dropped.
- **Duplicate Key in `executeAction`** *(bugfix)*: Fixed a duplicate key issue in the `executeAction` implementation.

## `v1.2.3`

- **Fetcher Error Handling** *(bugfix)*: Fetcher components now display a localized error message when the fetch request throws an unexpected exception, instead of throw an uncaught exception.

## `v1.2.2`

- **Fetcher Rendering Bug** *(bugfix)*: Fixed issue where successful fetcher results would never actually load.

## `v1.2.1`

- **Opinion Icon Tie-Breaking** *(bugfix)*: When multiple opinions are tied by count, the icon now consistently displays the highest-severity opinion (malicious > suspicious > obscure > benign) instead of depending on annotation order.

## `v1.2.0`

- **Action Configuration Button** *(new feature)*: Added a configuration button to the action interface for managing action settings.
- **Force Menu and Execution Context** *(new feature)*: Added ability to force menu items to appear and pass contextual information when executing actions.
- **Async Fetcher Results** *(new feature)*: Fetchers can now return results asynchronously, improving responsiveness for long-running lookups ([#35](https://github.com/CybercentreCanada/clue/pull/35)).
- **File Result Type** *(new feature)*: Actions and fetchers can now return file results, enabling file-based output handling ([#38](https://github.com/CybercentreCanada/clue/pull/38)).
- **Execute Action Popover Improvements** *(improvement)*: Improved the layout and behaviour of the Execute action popover menu ([#40](https://github.com/CybercentreCanada/clue/pull/40)).
- **Assemblyline and Howler Icons** *(new feature)*: Added icons for Assemblyline and Howler integrations ([#32](https://github.com/CybercentreCanada/clue/pull/32)).
- **Plugin Dashboard** *(bugfix)*: Fixed and improved the plugin dashboard display ([#43](https://github.com/CybercentreCanada/clue/pull/43)).
- **Action Result Modal** *(bugfix)*: Fixed the action result modal getting stuck in a loading state indefinitely ([#37](https://github.com/CybercentreCanada/clue/pull/37)).
- **Newlines in Annotation Summaries** *(bugfix)*: Newline characters in annotation summaries are now rendered correctly ([#46](https://github.com/CybercentreCanada/clue/pull/46)).
- **Case-Sensitive Annotation Subquery** *(bugfix)*: Fixed case sensitivity handling in the `useAnnotations` subquery.
- **Selector Value Input** *(bugfix)*: Fixed spaces being incorrectly disallowed in the selector value input box.
- **Raw Data and Timestamps** *(bugfix)*: Fixed raw data display and added timestamp support ([#41](https://github.com/CybercentreCanada/clue/pull/41)).

## `v1.1.5`

- **Status Collection Checks** *(bugfix)*: Added additional status collection checks to prevent errors on incomplete collections.
- **Closed Collection Enrichment Guard** *(bugfix)*: Added a check to skip enrichment queuing for closed collections.
- **Pinned react-router Versions** *(bugfix)*: Pinned react-router dependency versions to prevent regressions from upstream updates.

## `v1.1.0`

- **French Translation** *(new feature)*: Added French translation support (README.fr.md).
- **Documentation Build Pipeline** *(technical update)*: Updated the documentation build pipeline.
- **Navigation** *(improvement)*: Enhanced navigation with mkdocs-awesome-nav integration.

## `v0.14.0`

- **Plugin Documentation** *(new feature)*: Added plugin documentation pages.
- **User-Set Typing** *(new feature)*: Added the ability for users to set types manually in Clue.
