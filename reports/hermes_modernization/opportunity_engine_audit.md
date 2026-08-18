# Opportunity Engine Audit

## Scope

This audit searched for existing Nexus opportunity, revenue, research, marketing, affiliate, SEO, and monetization surfaces before adding a canonical opportunity model.

## Existing surfaces found

| Component | Role | Classification |
| --- | --- | --- |
| `scripts/client_flow/build_business_opportunities.py` | Existing opportunity build entrypoint | EXTEND |
| `src/lib/hermesSupabaseContextAdapter.ts` | Maps `business_opportunities`, `offers_summary`, and `revenue_summary` into Hermes context | WRAP |
| `src/lib/hermes/hermesOperatingContext.ts` | Synthesizes revenue and opportunity recommendations | WRAP |
| `src/lib/hermes/hermesGeneralTools.ts` | Read-only revenue summary tool | KEEP |
| `src/lib/nexusReadinessRegistry.ts` | Readiness / opportunity / affiliate / marketing status source | EXTEND |
| `src/lib/hermesConversationEngine.ts` | Existing conversational routing | KEEP |
| `src/lib/hermesConversationBrain.ts` | Existing response shaping | KEEP |
| `src/lib/hermesReferenceResolver.ts` | Existing reference resolution for recommendation lists | KEEP |
| `reports/alpha/alpha_independent_research_intake_audit.md` | Research intake inventory | WRAP |
| `reports/alpha/alpha_brain_readiness_audit.md` | Alpha role / opportunity readiness analysis | WRAP |
| `reports/alpha/seo_money_opportunity_candidates.md` | SEO monetization candidates | EXTEND |
| `reports/alpha/opportunities/*` | Research-derived opportunity artifacts | MERGE |
| `scripts/nexus_agent_platform/loops/runtime.py` | Opportunity discovery loop runtime | EXTEND |
| `scripts/nexus_agent_platform/tests/test_opportunity_engine.py` | Deterministic opportunity engine tests | EXTEND |

## Reconciliation outcome

- No duplicate persistent opportunity store was added.
- The new canonical opportunity model is a read-only normalization layer over existing governed reads and research artifacts.
- Existing Hermes / Alpha / readiness surfaces are reused rather than replaced.
- The new engine is `CREATE_NEW` only for the canonical model and deterministic scoring contract.

## Existing capability groups

- KEEP: conversational routing, reference resolution, read-only summary tools
- EXTEND: readiness registry, business opportunity source, Alpha research opportunities, loop runtime
- WRAP: Hermes operating context, Supabase context adapter, Alpha audit artifacts
- MERGE: research-derived opportunity artifacts into canonical model input
- CREATE_NEW: canonical opportunity model / scoring / dedupe contract

## Cost accounting audit

- `estimated_cost` in loop benchmark output is **USD dollars**, not an abstract score.
- Verified unit check: `_cost_for_tier("T1_CHEAP_AI", 163, 270) == 0.2165`
- Calculation: `(163 + 270) * 0.0005 = 0.2165`
- No unit/scaling bug was found in the loop cost formula.

## Notes

- Deterministic scoring remains Python-first.
- AI is used only for interpretation or synthesis when the deterministic threshold is crossed.
- The opportunity engine does not create a competing opportunity identity or store.
