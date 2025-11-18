# Clue API Release Notes

## `v0.13.0`

- Added plugin documentation
- Refactored `ip` type to `ipv4` and `ipv6`
- Fixed bug in domain regex that would not match against `doublehypenated--domains.com`
- Added ability for actions to accept no selectors (`accept_empty`)
- Added check to catch expired tokens in token cache instead of using them anyway
- Added improved validation of enrichment parameters
- Added fix for enrichments not returning any entries if a single entry is too high of a classification
