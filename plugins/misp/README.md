# Misp

Maintaining Team/Organization: Monjiapawne

Point of Contact: Monjiapawne <iambrendamore@gmail.com>

Status: In Development

This plugin interfaces with MISP's API


## notes

Trade offs

- guarded for multiple tlp tags
- opted for colating all misp events into single QueryEvent
- opted for taking the attributes tlp if there is one, if not the highest TLP of the of the event
- fallbacks in general for event level vs attr
