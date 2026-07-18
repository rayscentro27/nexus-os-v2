# Nexus Competitive Feature Gap Map

Generated: 2026-07-18

This map compares feature patterns, not product mandates.

| Feature pattern | Comparator examples | Nexus status | Gap class | Recommendation |
|---|---|---|---|---|
| Webhook-backed one-time payment | Stripe samples | ALREADY_SOLVED | ALREADY_SOLVED | Preserve test-mode path; live deferred. |
| Subscription billing lifecycle | Kill Bill, Stripe Billing | DEFERRED | VALUABLE | Separate sprint only after controlled customer testing. |
| Executive operating dashboard | ERPNext, Metabase | PARTIAL | CRITICAL | Build Founder Mode Core first. |
| Ray approval/HITL queue | LangGraph HITL, n8n manual gates | PARTIAL | CRITICAL | Consolidate `task_requests` and `approvals`. |
| Capability registry | Appwrite/Supabase console patterns, internal registries | PARTIAL/DUPLICATED | CRITICAL | Create canonical read model in Wave 1/2. |
| System health dashboard | Metabase/admin consoles | PARTIAL/DUPLICATED | CRITICAL | Canonicalize Supabase health + report evidence. |
| Repo-intelligence lane | internal research/adapters | PARTIAL/DISCONNECTED | VALUABLE | Run parallel read-only lane with Ray Review hooks. |
| Client portal and readiness workflow | CRM/customer portals | IMPLEMENTED | ALREADY_SOLVED | Do not redesign in Founder Mode sprint. |
| Document processing lifecycle | Paperless-ngx, MarkItDown | PARTIAL | VALUABLE | Study only; sandbox before dependencies. |
| Support inbox/customer communication | Chatwoot | PARTIAL/BLOCKED | VALUABLE | Manual/checklist first; provider sends approval-gated. |
| CRM/client pipeline | Twenty, ERPNext | PARTIAL | VALUABLE | Improve admin/client pipeline after Founder Mode. |
| Marketing/social scheduling | Postiz, Mixpost, Mautic | BLOCKED | OPTIONAL | Keep draft-only until legal/provider approval. |
| Visual automation workflows | n8n, Huginn | PARTIAL/UNSAFE | OPTIONAL | Do not integrate before capability governance. |
| Knowledge/evidence layer | RAG/eval frameworks | PARTIAL | VALUABLE | Wave 3 after Founder Mode and capability registry. |
| Trading execution | Freqtrade, LEAN | BLOCKED | NOT_ALIGNED for Wave 1 | Keep research/backtest only. |

## Critical gaps before Founder Mode can be called complete

1. One executive source of truth for Ray.
2. One approval authority model.
3. One work/request/job lifecycle.
4. One system-health summary.
5. Clear Hermes/Alpha/client-AI separation.

## Already solved or recently certified

- Nexus 3 client shell and authenticated client routes.
- Credit/Business exact page replacement.
- Admin route guard.
- RLS tenant isolation.
- Stripe test-mode one-time review flow foundation.
- Alpha no-Supabase guard.

## Not aligned for first implementation wave

- Live Stripe.
- Subscriptions.
- Trading execution.
- Public publishing.
- Broad external automation.
- Heavy third-party platform installation.
