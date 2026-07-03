# Hermes Access Capability Audit

Date: 2026-07-02

## Scope and method

This is a read-only code, adapter, report-registry, and UI-route audit. It did not query paid APIs, mutate Supabase, activate schedules, publish, send, charge, trade, or deploy. Production authentication was not available to this local audit, so live-only claims remain partial, blocked, or unknown.

## Access matrix

| Area | Status | Read | Summarize | Open | Draft | Execute | Primary blocker / boundary |
|---|---|---:|---:|---:|---:|---:|---|
| Approvals / Ray Review | connected | yes | yes | yes | yes | no | Decisions remain approval-gated |
| Reports | connected | yes | yes | yes | no | no | Local report snapshots |
| Clients | blocked | yes | yes | yes | no | no | `client_profiles` production access denied |
| Business Opportunities | partial | yes | yes | yes | yes | no | Mixed live/static provenance |
| System Health | partial | yes | yes | yes | no | no | Report-backed, not a live production probe |
| Research to Money | partial | yes | yes | yes | yes | no | Scheduler/connectors need verification |
| Creative Studio | partial | yes | yes | yes | yes | no | Dedicated source adapter missing |
| Revenue Dashboard | partial | yes | yes | yes | yes | no | Payment evidence needs authenticated verification |
| Hermes Advisor Inbox | connected | yes | yes | yes | yes | no | Report snapshot |
| Scheduler / Automation | approval_gated | yes | yes | yes | yes | no | Activation requires approval |
| YouTube Research | partial | yes | yes | yes | yes | no | Some approved source files missing |
| Credit & Funding Readiness | partial | yes | yes | yes | yes | no | Client evidence currently blocked |
| Specialist Agents | partial | yes | yes | yes | yes | no | No verified live agents registered |
| Page / UI Context | connected | yes | yes | no | no | no | Metadata is not verified operational data |
| Trading / Oanda / Vibe | blocked | yes | yes | yes | no | no | Live/funded execution disabled |
| Email / Resend | not_configured | yes | yes | no | yes | no | Sender/key configuration incomplete |
| Stripe / Checkout | approval_gated | yes | yes | no | yes | no | Confirmation remains approval-gated |
| Supabase | partial | yes | yes | no | no | no | Table/session access varies |
| Netlify / Deployment | unknown | no | yes | no | no | no | No authenticated live adapter |
| Knowledge Base / Memory | partial | yes | yes | no | yes | no | Durable writes and freshness separately governed |

## Connected areas

Reports, Approvals/Ray Review, Hermes Advisor Inbox, and page-context metadata have usable adapters or registries. Page context is explicitly not treated as live source evidence.

## Partial areas

Business opportunities, system health, research, Creative Studio, revenue, YouTube, credit/funding, specialist inventory, Supabase, and memory have useful local or scoped context but lack at least one live or dedicated verification path.

## Blocked and not configured

Clients are blocked by the observed `client_profiles` access denial. Live/funded trading is blocked by policy and incomplete practice verification. Resend is not configured for a verified send path. Deployment status is unknown without authenticated Netlify verification.

## Approval-gated areas

Schedulers, Stripe/payment confirmation, approval decisions, and any external execution remain approval-gated. Hermes can open their review screens and prepare conversation-only drafts; it cannot execute them.

## Missing UI routes/actions

Reports and Ray Review have safe routes. Creative Studio, client detail selection, individual report deep links, individual approval deep links, source evidence, Stripe, Resend, and a dedicated access-map screen need richer route/deep-link support. Current metadata safely opens the parent screen.

## Missing source adapters

Dedicated adapters remain missing or incomplete for Creative Studio, Netlify deployment, Resend status, Stripe read-only status, specialist runtime inventory, and durable knowledge freshness.

## Recommended repair order

1. Restore authenticated read-only `client_profiles` access.
2. Add read-only Netlify/deployment verification.
3. Add dedicated Stripe and Resend status adapters without execution authority.
4. Add item-specific report and approval deep links.
5. Add Creative Studio and specialist runtime inventories.

