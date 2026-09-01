# Hermes volatile-state repair

`turn_requirements` now treats present-tense signals including “currently”,
“still”, “active”, and “right now” as freshness requirements. When prior
structured Nexus provenance exists, the current read is required again; prior
assistant text cannot substitute for it.

Fresh Nexus results remain authoritative over prior volatile context. The
canonical result observed was reviews=0, blockers=0, opportunities=0, and one
queued work item. Historical counts remain labeled historical in synthesis.

No Nexus currentness logic or Nova profile was changed.
