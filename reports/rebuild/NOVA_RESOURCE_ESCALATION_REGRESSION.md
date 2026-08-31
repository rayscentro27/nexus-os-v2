# Nova resource escalation regression

Using a fresh dedicated-profile Hermes session, resource use remained enabled:

- Tesla current-information test: 4 tool calls, including 2 searches and 2 retrievals.
- Nexus attention test: 2 Nexus reads.
- Alpha challenge test: 1 Alpha call.

All three returned generated responses. No phrase-specific resource route was
added; the existing semantic/resource contract and native Hermes tool calls
remain responsible for escalation.
