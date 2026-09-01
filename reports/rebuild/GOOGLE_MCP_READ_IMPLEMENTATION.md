# Google MCP Read Implementation

The implementation wraps the existing OAuth adapter and calls the official
Gmail and Calendar APIs only after refresh-only credential construction.

Every result includes resource, tool, source, fetched time, query, live-read
currentness, item count, warnings, request ID, and read-only status. Gmail
results are bounded to headers, IDs, labels, dates, and short snippets. Event
descriptions are intentionally excluded from MCP output to minimize personal
data exposure.

Availability is derived from the authorized Calendar event-read surface because
the existing grant did not include the broader free/busy scope. This avoids
requesting new authority while providing deterministic busy intervals.

Real local probes succeeded for Gmail search/message/thread and Calendar
search/event/availability projection. Today’s Calendar query returned an empty
live result; no fixture was used.
