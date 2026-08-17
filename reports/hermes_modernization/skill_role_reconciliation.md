# Nexus Hermes Modernization — Phase 3B Skill / Role Reconciliation

- Starting head: `05f3ac7f4742220ddd922b5dd1e5017461556eee`
- Scope: reconcile the 11 new plugin skills against existing agents, specialist profiles, routers, capability layers, and operational modules
- Outcome: no new persistent identity is required for any of the 11 skills

## Audit Summary

The existing repository already has three persistent agent identities:

- `nexus_hermes` — internal operator / chief-of-staff
- `hermes_nova` — governed conversational adviser
- `alpha` — outside-thinking research adviser

Everything else in this reconciliation belongs to one of four buckets:

- deterministic capability layers
- specialist profiles / role configs
- report or workflow modules
- temporary or bounded skill wrappers

That means the 11 new skills should be treated as reusable skill wrappers, not new long-lived personalities.

## Skill Reconciliation

| Skill | Existing equivalent | Owner | Agent | Existing module / routing | Existing tools | Overlap | Conflict | Token risk | Recommended action | Tier |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| `nexus-operator` | Hermes operator / chief-of-staff and capability router | Hermes | `nexus_hermes` | `scripts/nexus_agent_platform/agents/hermes.py`, `scripts/nexus_agent_platform/capabilities/shared.py`, `scripts/nexus_agent_platform/capabilities/nexus_knowledge.py` | `nexus_capability_lookup`, `nexus_system_status`, `nexus_process_status`, `nexus_runtime_status`, `nexus_pending_approvals` | 90% | medium | low | `EXTEND_EXISTING` | `T0_DETERMINISTIC` |
| `nexus-research-director` | Alpha research mode + study layer | Alpha | `alpha` | `scripts/nexus_agent_platform/agents/alpha.py`, `scripts/nexus_agent_platform/capabilities/shared.py`, `scripts/nexus_agent_platform/capabilities/nexus_study.py` | `nexus_research_status`, `nexus_capability_lookup`, `nexus_system_status` | 85% | medium | medium | `WRAP_EXISTING` | `T1_CHEAP_AI` |
| `nexus-opportunity-director` | Alpha business-opportunity mode + opportunity/status reads | Alpha / Hermes opportunity modules | `alpha` | `scripts/nexus_agent_platform/agents/alpha.py`, `scripts/nexus_agent_platform/capabilities/shared.py`, `reports/manual_publish/nexus_automation_control_center_latest.md` | `nexus_revenue_status`, `nexus_research_status`, `nexus_capability_lookup` | 80% | medium | medium | `WRAP_EXISTING` | `T1_CHEAP_AI` |
| `nexus-creative-director` | Creative studio / creative reports / bounded concept generation | Hermes / ops | none | `reports/manual_publish/nexus_automation_control_center_latest.md`, creative report artifacts | `nexus_research_status`, `nexus_revenue_status`, `nexus_capability_lookup` | 70% | low | medium | `KEEP_AS_NEW` | `T2_STANDARD_AI` |
| `nexus-marketing-director` | Marketing specialist + SEO/affiliate/content automation categories | Hermes / ops | none | `configs/specialist_registry.json`, `configs/specialist_personality_profiles.json`, `reports/manual_publish/nexus_automation_control_center_latest.md` | `nexus_marketing_status`, `nexus_research_status`, `nexus_capability_lookup` | 85% | medium | medium-high | `MERGE_WITH_EXISTING` | `T1_CHEAP_AI` |
| `nexus-seo-director` | SEO marketing automation + research keyword tooling | Hermes / ops | none | `scripts/research/seo_keyword_scout.py`, `scripts/research/content_opportunity_lab.py`, `reports/manual_publish/nexus_automation_control_center_latest.md` | `nexus_research_status`, `nexus_opportunity_director`, `nexus_capability_lookup` | 80% | low-medium | low | `MERGE_WITH_EXISTING` | `T0_DETERMINISTIC` |
| `nexus-credit-readiness` | Credit specialist + funding readiness reads | Hermes / credit specialist | none | `scripts/nexus_agent_platform/capabilities/shared.py`, `configs/specialist_registry.json`, credit repair workflow reports | `nexus_funding_readiness_summary`, `nexus_credit_summary`, `nexus_client_summary` | 95% | medium | low | `EXTEND_EXISTING` | `T0_DETERMINISTIC` |
| `nexus-credit-result-verification` | Credit report / result verification workflow | Credit specialist / client workflow | none | `scripts/client_workflow/*`, `scripts/client_flow/*`, `scripts/compliance/classify_claim_risk.py`, `reports/credit_repair/*` | `nexus_credit_summary`, `nexus_client_summary`, `nexus_capability_lookup` | 90% | medium | low | `MERGE_WITH_EXISTING` | `T0_DETERMINISTIC` |
| `nexus-business-foundation` | Business foundation / bankability / readiness summary | Funding specialist / Hermes | none | `scripts/nexus_agent_platform/capabilities/nexus_study.py`, `scripts/nexus_agent_platform/capabilities/shared.py`, `configs/offer_registry.json` | `nexus_business_foundation_summary`, `nexus_revenue_status`, `nexus_system_status` | 80% | low-medium | low | `WRAP_EXISTING` | `T0_DETERMINISTIC` |
| `nexus-funding-readiness` | Funding readiness capability and client-scoped readiness reads | Funding specialist | none | `scripts/nexus_agent_platform/capabilities/shared.py`, client workflow and readiness artifacts | `nexus_funding_readiness_summary`, `nexus_client_summary`, `nexus_credit_summary` | 95% | medium | low | `EXTEND_EXISTING` | `T0_DETERMINISTIC` |
| `nexus-crj-handoff` | CRJ / client-success handoff packaging | Client success / credit workflow | none | `scripts/client_workflow/*`, `scripts/client_flow/*`, `reports/credit_repair/*`, `configs/specialist_registry.json` | `nexus_business_foundation_summary`, `nexus_revenue_status`, `nexus_capability_lookup` | 75% | low | medium | `REMOVE_DUPLICATE` | `T0_DETERMINISTIC` |

## Persistent Agents After Reconciliation

- `nexus_hermes`
- `hermes_nova`
- `alpha`

No new persistent identity is justified for any of the 11 skills.

## Role Conflicts

- `nexus-operator` overlaps directly with Hermes operator responsibility; keep it as a skill wrapper, not a new agent.
- `nexus-research-director` overlaps with Alpha research identity and the study layer; route it through Alpha or bounded study reads.
- `nexus-opportunity-director` overlaps with Alpha business-opportunity mode and Hermes opportunity modules; do not create a second opportunity personality.
- `nexus-marketing-director` and `nexus-seo-director` overlap with the existing marketing / SEO automation categories in the control-center taxonomy.
- `nexus-credit-readiness`, `nexus-credit-result-verification`, `nexus-business-foundation`, `nexus-funding-readiness`, and `nexus-crj-handoff` overlap with existing credit/funding/client-success workflow concepts and should stay read-only and governed.

## Token Duplication Risks

- Repeated model synthesis over the same research context for `nexus-research-director` and `nexus-opportunity-director`.
- Duplicate planning language for marketing / SEO when the repository already has bounded automation categories for `seo_marketing`, `affiliate_marketing`, and `content_opportunity_lab`.
- Duplicate credit/funding narrative generation when the core outputs are already deterministic reads from `get_funding_readiness`, `get_client_profile`, and the credit workflow artifacts.
- CRJ handoff becoming a second client-success layer instead of a packaging step.

## Phase 4 Loop Contract

The loop framework is defined now, but not implemented yet. A loop must be token-aware by construction.

### Required contract fields

- `loop_id`
- `name`
- `owner`
- `trigger`
- `goal`
- `inputs`
- `deterministic_precheck`
- `delta_only`
- `cache_enabled`
- `dedupe_enabled`
- `deterministic_steps`
- `ai_steps`
- `model_tier`
- `max_ai_calls`
- `max_input_tokens`
- `max_output_tokens`
- `estimated_token_budget`
- `cost_ceiling`
- `verifier`
- `retry_policy`
- `max_retries`
- `stop_if_no_change`
- `stop_conditions`
- `approval_boundary`
- `output`
- `memory_write_mode`
- `metrics`

### Required metrics

- `executions`
- `zero_token_executions`
- `ai_executions`
- `tier1_calls`
- `tier2_calls`
- `tier3_calls`
- `input_tokens`
- `output_tokens`
- `estimated_cost`
- `successful_outputs`
- `value_events`
- `tokens_per_success`
- `cost_per_success`

### Loop rules

1. Deterministic precheck first.
2. If no change, stop with zero model tokens.
3. Operate on deltas, not full history.
4. Reuse cached prior state.
5. Deduplicate inputs before any AI call.
6. Keep context compact and structured.
7. Enforce max AI calls per run.
8. Enforce max token budget per run.
9. Use the lowest reliable model tier.
10. Escalate to a premium tier only by explicit rule.
11. Let the verifier decide whether another AI call is justified.
12. Write compact structured memory only.
13. Never carry huge conversational transcripts between runs.
14. Track deterministic vs AI execution ratio.
15. Track tokens consumed per useful output.

### First loops to implement later

- `system_health_loop`
  - Owner: Hermes
  - Goal: detect operational drift with mostly zero-token execution
  - Model tier: `T0_DETERMINISTIC`
  - Max AI calls: `0`
  - Stop if no change: `true`

- `opportunity_discovery_loop`
  - Owner: Hermes / opportunity engine
  - Goal: collect, dedupe, score, and selectively synthesize promising opportunities
  - Model tier: `T1_CHEAP_AI`
  - Max AI calls: `1` unless verifier explicitly escalates
  - Deterministic precheck: required
  - Stop if no change: `true`

### Contract verdict

- Loop contract: `PASS`
- Broad loop implementation: `NOT STARTED`
