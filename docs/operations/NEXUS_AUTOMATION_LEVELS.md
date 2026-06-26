# Nexus Automation Levels

Nexus automation is classified **category-by-category**, never as one generic switch. Every
automation action falls into one of three levels.

**Core rule:** Nexus can work internally. Nexus cannot leave the building without approval.

"Leave the building" = publish, send, contact, trade, spend, deploy, schedule persistent jobs,
change production, connect sensitive systems, or expose private/client data externally.

Source of truth: `src/config/nexusAutomationLevels.ts`, classifier in
`src/lib/nexusAutomationPolicy.ts` (Python mirror: `scripts/automation/automation_model.py`).

## Level 1 — Autonomous Internal Automation (`autonomous_internal`)

- Allowed after the resource/process/category is approved. **No Ray approval per item.**
- `approval_required: false`, `ray_review_required: false`.
- Allowed outputs: internal cards, scores, reports, proof events, Hermes prep, department routing,
  internal recommendations.
- Forbidden: publish, send, trade, spend, deploy, scheduler activation, client contact.
- Examples: research, scoring, routing, internal cards/reports, transcript review, SEO keyword
  scoring, affiliate opportunity scoring, Hermes prep briefs, paper-only strategy research.

## Level 2 — Approval-Gated Automation (`approval_gated`)

- Can **prepare** work automatically, but Ray must approve before **execution**.
- `approval_required: true`, `ray_review_required: true`, rollback plan required.
- Allowed before approval: drafts, proposals, campaign packages, scheduler candidates, connector
  setup recommendations, reports, decision briefs.
- Forbidden before approval: external execution, outbound contact, public publishing, live
  spending, production mutation.
- Examples: campaign publishing, social posts, email/SMS/DM sending, client/lead contact,
  ad/spend decisions, scheduler activation, connector activation, production changes.

## Level 3 — Blocked / High-Risk Automation (`blocked_high_risk`)

- **Default state: blocked.** Not allowed unless separately designed, explicitly approved, and
  protected by its own contract.
- Requires: separate design doc, explicit Ray approval, proof plan, rollback plan, hard guard
  tests, safety contract.
- Examples: live trading, broker execution, funded account actions, raw `auto_executor` exposure,
  payment/spend actions, production deploys, credential changes, destructive database actions,
  broad scraping, YouTube media downloads, external AI on sensitive/private/customer data.

## How each system uses these levels

- **Ray Review Queue:** Level 1 never enters. Level 2 enters when execution-ready. Level 3 enters
  only as a blocked/escalation card — never as an executable approval.
- **Approvals:** Level 1 → no approval row. Level 2 → approval row only when execution-ready.
  Level 3 → no direct execution approval; separate contract/design review first.
- **Scheduler Approval Center:** generates proposal-only candidates with their level; activation is
  always Level 2 and never auto-applied.
- **Hermes / Jarvis:** may recommend at any level, but only executes Level 1 internally; Level 2
  needs Ray approval; Level 3 is escalation-only.

## Adding future automation safely

1. Classify the action with `classifyAutomationLevel()`.
2. If Level 1, ensure outputs stay internal (cards/scores/reports/proof).
3. If Level 2, prepare drafts/proposals only; route execution through Approvals + Ray Review Queue.
4. If Level 3, write a separate design doc + safety contract + hard guard test before anything runs.
