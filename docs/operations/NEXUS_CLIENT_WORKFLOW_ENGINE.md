# Nexus Client Workflow Engine (GoClear / Apex)

The backend operating brain that moves a client from signup to funding-ready. This is the engine
layer (processes, models, scoring, reports, Hermes recommendations, Command Center visibility) — not
a final UI redesign.

Core principle: **Nexus can work internally; it cannot leave the building without approval.** Final
client-facing recommendations are NEVER exposed until Ray approves. See
[NEXUS_AUTOMATION_LEVELS.md](NEXUS_AUTOMATION_LEVELS.md) and
[NEXUS_CLIENT_INTAKE_AUTOMATION_POLICY.md](NEXUS_CLIENT_INTAKE_AUTOMATION_POLICY.md).

## Source of truth

- Models: `src/config/clientWorkflow.ts`, `src/config/clientWorkflowReminders.ts`,
  `src/config/clientWorkflowAffiliate.ts`.
- Engines: `src/lib/clientWorkflowEngine.ts` (status/scoring), `src/lib/clientWorkflowHermes.ts`
  (proactive recommendations).
- Tables: `supabase/migrations/20260629090000_client_workflow_engine.sql` (re-versioned from unapplied `0012`; admin-only RLS, sensitivity-labeled).
- Scripts: `scripts/client_workflow/*` (Python mirror `client_workflow_model.py` + 6 generators/verifier).
- Command Center: `ClientWorkflowCard` in `src/components/command-center/MissionControl.tsx`.

## Workflow stages

`signup_started → profile_created → credit_report_source_needed → credit_report_pending →
credit_report_received → credit_analysis_ready → business_setup_needed → business_setup_in_progress →
business_analysis_ready → letters_needed → letters_ready → mailing_needed → funding_readiness_pending →
ray_review_needed → approved_client_plan_ready → client_plan_visible → funding_ready`

Each client tracks current_stage, next_required_action, due_at, days_stuck, progress_percentage,
funding_readiness_impact, revenue_risk_level, ray_review_status, and client_visible_status.

## Credit report source

- **SmartCredit (recommended, affiliate):** score visibility/monitoring; affiliate disclosure shown;
  NOT required. No password storage, no scraping, no automated login.
- **AnnualCreditReport.com (free official):** reports only; manual score entry allowed; no affiliate
  language.
- **Manual upload (other):** upload an existing report.

## SmartCredit connector shell

Statuses: `not_configured | affiliate_link_only | partner_signup_ready | api_connected |
report_import_ready | disabled`. Default `not_configured`. Report download is
`requires_partner_api_confirmation` unless a verified partner/API endpoint is confirmed in config.
Allowed v1: affiliate click/signup tracking, manual report upload, placeholders, internal status,
Hermes recommendations.

## Credit score visibility

Score history per bureau/model/source with manual entry support. Disclaimer: scores vary by model,
bureau, lender, and timing; analysis is educational/planning only and is not a guarantee of approval,
deletion, score increase, or funding.

## Credit + business + funding scoring

`clientWorkflowEngine.ts` computes Credit Readiness, Business Foundation / Bankability, and Funding
Readiness scores, top blockers, missing setup items, and next actions. One Ray Review card is created
only when the full client-facing plan is ready — never per negative item.

## Business setup (partner vs DIY)

Every setup item (LLC, EIN, registered agent, address, phone, website, email, DUNS, bank account,
bookkeeping, vendor accounts, licenses, bank statements) offers a recommended partner AND a DIY/free
official option, with proof upload, verification, and bankability/funding impact. Nexus never files
LLC/EIN/state docs, opens accounts, or applies for vendor accounts automatically.

## Letters + mailing

Letter packets (bureau/creditor/collector disputes, validation, MOV, goodwill, pay-for-delete) are
drafted internally and are approval-gated. Mailing: **DocuPost** (online, connector shell only — no
auto-send, no postage spend) or **USPS Certified Mail** (DIY print + mail, client uploads receipt).
Nexus never mails letters, contacts bureaus/creditors, or spends postage.

## Reminders

Stuck-client detection + reminder DRAFTS are Level 1 (internal). Default timings: 24h urgent blocker,
3-day incomplete setup, 7-day stuck (Hermes escalation), 14-day Ray escalation. External
email/SMS/DM reminders require client opt-in + approval — no auto-send in v1.

## Hermes department layer

On entering the department, Hermes proactively surfaces stuck clients, missing tasks, credit/score
gaps, business gaps, unmailed letters, missing mailing proof, funding blockers, Ray-review-ready
clients, upsell/affiliate opportunities, near-funding-ready clients, revenue risk, and
"do-not-send-to-lenders" warnings. Output is internal-only unless approved.

## Automation levels (summary)

- **Level 1 (autonomous):** status updates, credit/business/funding analysis, reminder drafts,
  stuck-client detection, Hermes prep, affiliate opportunity scoring.
- **Level 2 (approval-gated):** sending messages, client/lead contact, publishing the client plan,
  connector/scheduler activation, mailing letters, submitting disputes, applying for funding,
  exposing client recommendations.
- **Level 3 (blocked):** storing SmartCredit passwords, scraping SmartCredit, auto-submitting
  disputes, auto-mailing, auto-contacting bureaus/creditors, auto-filing LLC/EIN/state docs,
  auto-opening accounts, auto-applying for funding, external AI on private client credit data.
