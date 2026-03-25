# Clue UI Release Notes

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
