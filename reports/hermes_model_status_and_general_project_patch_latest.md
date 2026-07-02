# Hermes Model Status and General Project Patch

Generated: 2026-07-01 19:46 America/Phoenix

- Model-use questions answer from the last trace when present and fall back to honest capability/configuration status when absent.
- No-trace answers do not claim that the previous response used a model.
- General house/app/project questions now use planning-only `general_project_planning`.
- Lightweight token normalization handles common advisor typos without changing technical identifiers broadly.
- Clarification replies resume a stored unresolved question through four-turn `fallback_continuation` state instead of repeating fallback.
- Explicit Nexus builds retain Nexus planning; explicit implementation remains approval-gated.
- 559/559 tests and the production build passed.
- Browser verification remains blocked by authenticated admin sign-in.
