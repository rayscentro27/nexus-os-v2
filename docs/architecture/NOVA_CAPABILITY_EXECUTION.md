# Nova Capability Execution

Nova keeps the five-stage brain graph. Capability execution is an invocation
inside `generate_response`, after Nova has reasoned and optionally emitted the
strict `nova_capability_request` envelope.

The broker validates the requested capability; the shared capability adapter
enforces read, privacy, cost, and authority boundaries. A bounded result or
structured failure is returned to Nova for synthesis. A failed provider is not
a user-facing answer by itself.

Allowlisted execution currently includes public search, public page retrieval,
and bounded Alpha research. Nexus requests remain submit-only; Nexus validates
and executes any consequential work. Search is free-first: SearXNG, then the
credential-free HTML fallbacks, with paid providers never selected as an
unapproved requirement.

Evidence remains provenance-bearing. Search discovery, page retrieval, Alpha
artifacts, and Nexus receipts are separate claims and are not interchangeable.
