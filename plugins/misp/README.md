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
- fall back to guaranteed fields always
- not falling back to event tags, too risky to have misleading tags
- chose to derive the quantity from the confirmed sightings, this might not be the standard usage
- chose to fallback to event creation time instead of attribute modification time

- opted to show "no sightings found" if there were no reported sightings, however users of misp rarely report sightings so this may just add noise to annoations, subject to removal and only show when there are sightings
- included event level rating in grouping of tags
