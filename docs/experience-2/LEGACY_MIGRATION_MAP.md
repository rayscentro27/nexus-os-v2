# Legacy Migration Map

**Disposition in this phase:** documentation only. No legacy component is deleted or rerouted.

## Current shell inventory

The current Admin navigation exposes **26 direct items**: 7 Executive, 2 agent items, 13 Business items, and 4 System items. This is the exact count observed in `src/admin/NexusAdminUI.jsx` at the design-reset starting commit.

## Proposed map

| Current entry/path | Future home | Disposition |
| --- | --- | --- |
| Command Center | Command | Move under new front door |
| Mission Control V2 | System → Mission Control | Move; diagnostic source remains |
| Nexus Operations | Work | Merge into Work presentation |
| System Health | System | Merge into Mission Control/runtime detail |
| Ray Review | Work → Needs You / Approvals | Merge presentation; retain canonical approval source |
| Hermes Workroom | Agents → Hermes | Replace visual shell after cutover |
| Reports | Studio → Reports / Artifacts | Move and merge with artifact presentation |
| Nova | Agents → Nova | Replace visual shell after cutover; preserve transport |
| Hermes Alpha | Agents → Alpha / Studio → Research | Replace visual shell; preserve research route |
| Clients | Business → Clients | Move into Business |
| Credit & Funding | Business → Credit & Funding | Move and consolidate |
| Credit & Funding Readiness Review | Business → Credit & Funding | Merge into journey context |
| Tester Readiness | System → Diagnostics | Diagnostic-only; never primary |
| Tester Invitations | System → Diagnostics | Diagnostic-only; never primary |
| Readiness Intake | Business → Credit & Funding | Merge into client/readiness context |
| Readiness Review | Work → Needs You + Business | Merge decision view with canonical review source |
| Business Opportunities | Business → Opportunities | Move |
| Research Engine | Studio → Research | Move; hide implementation label |
| Monetization | Business → Revenue | Merge into revenue context |
| Revenue Activation | Business → Revenue | Merge; preserve governance and test truth |
| Outsourced Fulfillment | Work / Business | Move to work detail; not primary |
| Marketing Drafts | Studio → Campaigns | Move |
| Trading Demo | System → Diagnostics | Diagnostic-only; funded/live trading remains disabled |
| Automation Scheduler | System → Workers | Move; do not expose scheduler as product model |
| CLI / Tool Registry | System → Diagnostics | Diagnostic-only |
| Settings | System | Keep as account/system detail |

## Duplicate render paths to retire after cutover

- Legacy Admin shell in `src/admin/NexusAdminUI.jsx` becomes compatibility shell, then deprecates after browser review.
- Generic Hermes helper/input and launcher/drawer remain compatibility paths until the universal composer is canonical.
- `HermesWorkroom → SpecialistWorkroom → HermesChatPanel` legacy visual shell is replaced by the shared Agent thread presentation while retaining its canonical send path.
- Legacy Alpha dashboard presentation becomes the Alpha agent/research presentation.
- Legacy Mission Control presentation remains a System diagnostic view, not the front door.

## Cutover guardrails

1. Route the new shell behind a reversible feature boundary.
2. Browser-certify Command, Work, Agents, Business, Studio, and System.
3. Confirm canonical sources and auth guards are still used.
4. Search imports/usages before deprecating a legacy component.
5. Remove only after a human visual review and rollback window.

No deletion is performed in the design reset.
