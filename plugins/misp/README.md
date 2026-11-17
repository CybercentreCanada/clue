# MISP

Maintaining Team/Organization: Monjiapawne

Status: In Development

MISP plugin enriches attributes, pulling data from attributes and their parent event.
Analysts can also report sightings back to MISP.

## Sightings

Sightings are submitted by value. MISP records one against every attribute matching that value, so a single report
can span multiple events.

The API key's role needs "Sighting Creator" permission.

## Changelog

### 0.3.0

- Expanded Clue type mappings and added composite MISP attribute types, including IP addresses with ports and filenames with hashes ([#113](https://github.com/CybercentreCanada/clue/pull/113)).

### 0.2.0

- Added ASN enrichment and sighting support, normalizing values with or without the `AS` prefix ([#106](https://github.com/CybercentreCanada/clue/pull/106)).

### 0.1.1

- Refactored enrichment handling. When annotations are requested, attributes without a last-seen or modification timestamp now produce an error instead of being silently skipped ([#95](https://github.com/CybercentreCanada/clue/pull/95)).

### 0.1.0

- Added an action to report true-positive or false-positive sightings by selector value ([#94](https://github.com/CybercentreCanada/clue/pull/94)).
