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
