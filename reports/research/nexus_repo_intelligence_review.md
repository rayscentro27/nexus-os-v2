# Nexus Repo Intelligence Review

Generated: 2026-07-18

## Status

RECONSTRUCTED_AND_RECONCILED

The prior repo-intelligence markdown reports existed, but the expected runtime registry `reports/runtime/nexus_repo_intelligence_registry.json` was missing. This audit reconstructed it as a sanitized, read-only registry.

## Recovered history

Existing artifacts found:

- `reports/research/nexus_repo_intelligence_review.md`
- `reports/research/nexus_top_repo_pattern_library.md`
- `reports/research/nexus_competitive_feature_gap_map.md`
- `reports/research/nexus_money_engine_recommendations.md`
- `reports/activation/open_source_repo_scout_for_alpha_and_nexus.md`
- `reports/activation/open_source_repo_priority_matrix.md`
- `reports/hermes_alpha/alpha_reference_project_evaluation.md`
- `reports/hermes_alpha/alpha_framework_research.md`
- `reports/runtime/nexus_active_operator_receipts/rcpt_repo_intelligence_*.json`
- `scripts/activation/run_repo_research.py`
- `scripts/activation/run_repo_concept_extraction.py`
- `scripts/research/extract_payment_repo_concepts.py`

Missing artifact:

- `reports/runtime/nexus_repo_intelligence_registry.json` was absent and has been reconstructed.

Git history:

- `0348176 activate Nexus operating engine dashboard client portal and work router` referenced repo-intelligence artifacts.

## Current Nexus overlap

| Area | Existing Nexus capability | Repo-intelligence implication |
|---|---|---|
| Stripe payments | Certified test-mode checkout/webhook/order/fulfillment | Study Stripe samples only; do not replace. |
| Supabase Auth/RLS/Storage | Implemented and certified | Study Supabase patterns; existing stack remains canonical. |
| Automation | Internal scripts, feeders, task requests, approvals | Study n8n/Huginn/Windmill patterns; do not integrate yet. |
| Support/CRM | Client/admin workflows exist | Study Chatwoot/Twenty/ERPNext patterns; no immediate dependency. |
| Research agents | Alpha local/mock providers and no-Supabase guard | Study LangGraph/CrewAI/Pydantic/Letta concepts only. |
| Documents | Private upload/storage and parser foundations | Study MarkItDown/Paperless patterns; file-processing sandbox required. |
| Trading | Backtest/demo research only | Study LEAN/vectorbt patterns; live trading blocked. |

## Candidate status

| Candidate | Status | Proposed disposition | Notes |
|---|---|---|---|
| Stripe Samples | RESEARCHED | STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY | Existing Stripe path is certified; sample patterns only. |
| Hyperswitch | RESEARCHED | STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY | Apache-2.0 metadata; overkill for first revenue loop. |
| Kill Bill | RESEARCHED | DEFER | Subscription lifecycle reference after one-time service is reliable. |
| BTCPay Server | RESEARCHED | DEFER | Future payment option only. |
| Docmost | RESEARCHED | REJECT | AGPL; document/wiki overlap not first priority. |
| Paperless-ngx | RESEARCHED | STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY | GPL; useful OCR/document lifecycle patterns, no code reuse. |
| Rocket.Chat | RESEARCHED | STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY | License unresolved by GitHub API; RBAC/channel patterns only. |
| Mattermost | RESEARCHED | STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY | License unresolved by GitHub API; collaboration patterns only. |
| Appwrite | RESEARCHED | STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY | Nexus already uses Supabase. |
| Supabase | INTEGRATED | REPLACE_WITH_EXISTING_NEXUS_CAPABILITY | Current backend source of truth. |
| n8n | RESEARCHED | DEFER | License unresolved/source-available concerns; external-action risk. |
| Huginn | RESEARCHED | STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY | Automation-agent concepts; do not run. |
| Metabase | RESEARCHED | STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY | Dashboard/query UX reference. |
| Plausible | RESEARCHED | STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY | AGPL; privacy analytics patterns only. |
| Chatwoot | RESEARCHED | STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY | Support workflow reference; license unresolved in API metadata. |
| Cal.com | RESEARCHED | DEFER | Scheduling not Wave 1. |
| Invoice Ninja | RESEARCHED | DEFER | Invoice patterns only; license unresolved. |
| Twenty | RESEARCHED | STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY | CRM pattern reference; license unresolved. |
| ERPNext | RESEARCHED | STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY | GPL; ERP workflow concepts only. |
| LangGraph | RESEARCHED | STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY | State-graph pattern useful after Founder Mode. |
| CrewAI | RESEARCHED | STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY | Role/delegation concepts only. |
| AutoGen | RESEARCHED | DEFER | Current repo metadata reports CC-BY; legal review required. |
| MarkItDown | RESEARCHED | DEFER | Useful for document normalization; sandbox needed. |
| Crawl4AI | RESEARCHED | DEFER | Public web extraction candidate; approval/cost controls required. |
| Firecrawl | RESEARCHED | DEFER | Existing Alpha URL-review foundation; live API not broadly activated. |
| LiveKit Agents | RESEARCHED | DEFER | Voice prototype later. |
| Pipecat | RESEARCHED | DEFER | Voice pipeline later. |
| LanceDB | RESEARCHED | DEFER | Local retrieval only when corpus need is proven. |
| Freqtrade | RESEARCHED | REJECT | GPL and execution surface; trading remains blocked. |
| LEAN | RESEARCHED | STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY | Research/backtest reference only. |
| vectorbt | RESEARCHED | DEFER | License unresolved by API metadata; research only. |

## Licensing state

GitHub API metadata was checked during this audit for candidate owner/repo, license SPDX where available, archived status, and recent activity. `NOASSERTION` or report-stated ambiguity means legal review is required before any dependency, code reuse, or hosted integration.

No GPL, AGPL, SSPL, source-available, network-copyleft, or ambiguous-license project is approved for integration.

## Security state

- No external repository was cloned, installed, vendored, or copied.
- No live provider credentials were configured.
- No Alpha Supabase access was enabled.
- No web crawler or social publisher was activated.
- No live trading or broker action was attempted.

## Evidence gaps

- Exact release-level licenses were not verified for every candidate.
- Security advisories were not exhaustively checked per exact release.
- Dependency trees were not reviewed.
- No legal review occurred.
- No implementation-cost estimate was proven by prototype.

## Recommended disposition

Repo Intelligence should be:

```text
B — parallel research lane with limited governance hooks in Wave 1
```

Wave 1 should show Repo Intelligence status, evidence, risk, and Ray Review hooks inside Founder Mode. It should not integrate external code or activate external services.
