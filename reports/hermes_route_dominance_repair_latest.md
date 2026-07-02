# Hermes Route Dominance Repair

Generated: 2026-07-02 05:48 America/Phoenix

- Confirmed fallback was last, not early; missing intent families made it appear dominant.
- Added dedicated system-health, current-page connection, current-page status, and scheduled-audit routes.
- Replaced system-health policy text with a user-facing checkpoint report.
- Both chat surfaces now pass route and section metadata with existing visible/selected context.
- Audit scheduling creates only a local approval-gated draft response and never starts a scheduler.
- Added farewell rendering and narrowly contextual `care`→`car` normalization.
- Fallback trace answers now identify a routing miss rather than claiming grounded local Nexus data.
- Approvals retrieval and selection-to-advisory continuity from `831dcc5` remain protected.
- 608/608 tests and the production build passed.
- Browser verification remains blocked by authenticated admin sign-in.
