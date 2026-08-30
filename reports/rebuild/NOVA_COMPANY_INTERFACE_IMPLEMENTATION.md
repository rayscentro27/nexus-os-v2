# Nova Company Interface Implementation

Campaign: `HG-WP6.5-NOVA-COMPANY-INTERFACE-NEXUS-COMMAND-AND-CAPABILITY-RECONCILIATION-20260830-01`

Implemented in this bounded checkpoint:

- `nova_company_context.py`: read-only projection over existing canonical brief/runtime sources.
- `nexus_command_acknowledgement.py`: typed RECEIVED/ASSIGNED/QUEUED/STARTED/terminal acknowledgement contract.
- Nova model context now receives the bounded company view only for company/Nexus-oriented questions; ordinary conversation remains lightweight.
- Canonical pending-approval capability alias repaired to `get_pending_approvals`.
- No new state store, framework, provider, credential, service, scheduler, or authority was added.

Existing Nova strengths retained: conversational-first response behavior, isolated memory, semantic capability gate, planner, provenance, model routing, and zero Nova writes. The company view does not replace TruthKernel or current evidence.

Real Telegram E2E is not claimed by this implementation checkpoint. The required live sequence remains pending.

## Live Nova wiring repair checkpoint

Campaign: `HG-WP6.5-NOVA-LIVE-COMPANY-INTELLIGENCE-AND-DELEGATION-REPAIR-20260830-01`

The observed failures were traced to bounded path/data issues rather than a new
architecture requirement:

- compound salutations could be rendered as greeting-only responses;
- the company view promoted an old report-backed brief and its priorities;
- pending-review reads used a legacy dashboard instead of the governed approval
  ledger;
- domain cues were evaluated too broadly, allowing research/state questions to
  use the wrong source;
- the existing governed recommendation API was not reachable for an explicit
  conversational delegation with a prior referent.

Repairs preserve ordinary conversation, read-only authority, and the existing
Nexus approval/execution boundary. A delegation creates only a bounded
recommendation record after a prior conversational referent is present; it does
not execute work or grant Nova write authority.

`136` focused tests pass. This is development evidence only. Fresh real
Telegram retesting is required for live certification of the six behaviors.
