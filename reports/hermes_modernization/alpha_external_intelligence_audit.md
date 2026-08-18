# Alpha External Intelligence Audit

## Scope

Alpha already exists as the persistent external-intelligence arm. This audit
reconciles existing Alpha research, routing, scoring, memory, and report
infrastructure before any extension.

## Existing Alpha capabilities

| Capability | Location | Classification |
| --- | --- | --- |
| Alpha agent graph and SOUL instructions | `src/hermes/alpha/alphaBrain.ts` | KEEP |
| Provider routing / status | `src/hermes/alpha/alphaProviderRouter.ts`, `src/hermes/alpha/alphaProviderStatus.ts` | KEEP / EXTEND |
| Provider bridge | `src/hermes/alpha/alphaProviderBridge.ts` | KEEP |
| Cost controller | `src/hermes/alpha/alphaCostController.ts` | KEEP |
| Memory | `src/hermes/alpha/alphaMemory.ts`, `src/hermes/alpha/hermesAlphaLocalMemory.ts` | KEEP |
| Research file adapter | `src/hermes/alpha/alphaResearchFileAdapter.ts` | KEEP / EXTEND |
| Web search | `src/hermes/alpha/alphaWebSearch.ts`, `scripts/hermes/hermes_web_search.py` | WRAP |
| URL review | `src/hermes/alpha/alphaUrlReview.ts` | WRAP |
| Scoring | `src/hermes/alpha/alphaScoring.ts` | KEEP |
| SEO money opportunities | `src/hermes/alpha/alphaSeoMoneyOpportunityEngine.ts` | KEEP / EXTEND |
| Trading research pipeline | `src/hermes/alpha/alphaTradingResearchPipeline.ts` | KEEP / EXTEND |
| Opportunity desk / marketing studio | `src/hermes/alpha/opportunityDesk.ts`, `src/hermes/alpha/marketingAssetStudio.ts` | KEEP / WRAP |
| Alpha conversation engine | `src/hermes/alpha/hermesAlphaConversationEngine.ts` | KEEP |
| Telegram worker | `scripts/alpha/alpha_telegram_worker.py` | KEEP |
| Live research bridge | `scripts/alpha/alpha_live_research.py` | EXTEND |
| Draft engine / opinion advisor | `scripts/alpha/alpha_draft_engine.py`, `scripts/alpha/alpha_opinion_advisor.py` | KEEP |
| Existing research pipelines | `scripts/research/*`, `scripts/activation/*`, `scripts/night_run/*` | MERGE / EXTEND |

## Repository findings

- Alpha already has live research, scoring, memory, route tracing, and report
  generation.
- Alpha already has research inboxes and curated report artifacts.
- Alpha already enforces PII and no-Supabase boundaries in its frontend and
  server-side code.
- Alpha already supports business opportunities, YouTube research, SEO, and
  trading research as distinct lanes.
- No second persistent research identity is needed.

## Classification summary

- KEEP: Alpha agent, provider routing, scoring, memory, conversation engine
- EXTEND: live research bridge, research file adapter, SEO/money opportunity
  tooling, trading research, repo/open-source research workflow
- WRAP: web search, URL review, opportunity desk, marketing studio
- MERGE: existing research pipeline scripts and report generators
- DEFER: new external sources until the existing adapters are reused
- REPLACE_ONLY_IF_PROVEN: none identified in this audit

## Open-source scout conclusion

The requested `nexus-open-source-scout` should be a workflow attached to Alpha,
not a new agent. It should:

1. Audit Nexus first for an existing capability or equivalent.
2. Classify Nexus state before any recommendation.
3. Score candidate repositories against maintenance, license, overlap, security,
   integration burden, and business value.
4. Output a governed recommendation only.
5. Stop before any installation or auto-adoption.

## Alpha role

Alpha remains the persistent external intelligence arm for public evidence,
market scanning, and opportunity interpretation. Hermes orchestrates. Nova stays
separate. No new persistent agent was created.
