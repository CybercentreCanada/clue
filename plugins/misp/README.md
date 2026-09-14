# MISP

Maintaining Team/Organization: Monjiapawne

Status: In Development

MISP plugin enriches attributes, pulling data from attributes and their parent event.
Analysts can also report sightings back to MISP.

## Sightings

Sightings are submitted by value. MISP records one against every attribute matching that value, so a single report
can span multiple events.

The API key's role needs "Sighting Creator" permission.
