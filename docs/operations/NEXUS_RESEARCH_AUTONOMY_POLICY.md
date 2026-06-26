# Nexus Research Autonomy Policy

Nexus runs research in two lanes.

## Lane 1: Autonomous Internal Research

Approval is not required for internal work after Ray approves the resource or source class:

- watching approved resources
- checking for new videos/articles/pages
- transcript review
- research scoring and re-scoring
- SEO keyword scoring
- affiliate opportunity scoring
- internal department routing
- internal project and experiment cards
- internal reports
- paper-only trading research cards
- Hermes internal recommendations and memory summaries

These actions stay inside Nexus and do not contact a lead, client, public account, broker, payment provider, ad account, or production system.

## Lane 2: Approval-Gated Execution

Approval is required for:

- publishing campaigns or social posts
- sending email, SMS, DM, or social outreach
- launching ads
- contacting leads, clients, or partners
- spending money
- live trading or broker execution
- enabling persistent schedulers
- production system changes
- using sensitive/private data in external tools
- any action that leaves Nexus or affects a client/public account

## Implementation

- `src/config/nexusResearchAutonomyPolicy.ts` defines the lane model.
- `src/config/nexusActionPolicy.ts` distinguishes internal review from approval-required execution.
- Research scripts default to `approval_required=false` for internal scoring/routing/reporting.
- Risk flags can request internal review without forcing Approvals.

Scheduler activation remains disabled until Ray approves it in a future Scheduler Approval Center.

## Ray Review Queue Boundary

Ray Review Queue is for true decisions only. It should not receive every scored transcript, SEO keyword, affiliate opportunity, watched resource update, internal report, or paper-only trading research card.

Review Queue items are created for outbound/risky execution decisions, connector/scheduler/production decisions, high-value strategic choices, and compliance-sensitive actions.

For Ray's watched YouTube resources, transcript/video scoring, routing, and reports are autonomous internal research. They should not create Ray Review Queue items unless a finding becomes campaign-ready, send-ready, scheduler-ready, client-contact, production-change, or live trading/execution-related.

## Automation Levels

This policy is the Level 1 (autonomous internal) lane of the universal model in
[NEXUS_AUTOMATION_LEVELS.md](NEXUS_AUTOMATION_LEVELS.md). Research, scoring, routing, internal
cards/reports, transcript review, SEO/affiliate scoring, Hermes prep, and paper-only trading
research are all Level 1 — autonomous after the category is approved, with nothing leaving the
building. The moment a finding would publish, send, contact, schedule, connect, deploy, or spend,
it becomes Level 2 (approval-gated) or Level 3 (blocked).
