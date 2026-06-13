# Misp

Maintaining Team/Organization: Monjiapawne

Point of Contact: Monjiapawne <iambrendamore@gmail.com>

Status: In Development

This plugin interfaces with MISP's API


## notes

Trade offs

- guarded for multiple tlp tags, selected highest of first the attribute then falling back to the event
- opted for colating all misp events into single QueryEvent
- chose to not to use event tags, too risky to have misleading not related to attribute
- Derive the quantity from the confirmed sightings
- Chose to fallback to event creation time instead of attribute modification time, if no attribute last seen
