# Nexus Hermes Modernization — Summary

**Status:** Phase 1A complete · Phase 1B isolated upstream Hermes compatibility lab proven · Phase 2 plugin boundary and initial skills added · Phase 3B skill / role reconciliation complete · Phase 4 loop runtime complete · Phase 5 opportunity engine foundation complete · Phase 5B cost accounting verified · Phase 6 Alpha external intelligence audit started · Phase 6B deterministic external intelligence proof complete · Phase 7 creative lab foundation complete
**Baseline HEAD:** `7c7625e` · Client Portal V2: COMPLETE / PROTECTED

## What Phase 0 established

1. **The system is already deterministic-first.** Every enabled schedule in the 70-entry automation registry is `internal_safe`; model routing is a deterministic policy layer; approvals are single-use with TTL; work orders are an idempotency-keyed state machine; media downloads, live Stripe, live trading, and public publishing are all disabled/approval-gated by policy.
2. **AI is already confined.** Only 4 processes make model calls (Hermes front brain, Nova, Alpha research, LiteLLM adapter), all gated and redacted. LangGraph exists as 3 thin graphs behind flags. No LangGraph exists for credit/outcome/funding reasoning — those stay deterministic (correct).
3. **The offer-engine target is still minimally additive.** The current gap list has advanced to the isolated upstream Hermes compatibility lab, plugin boundary, skills framework, loop framework, Opportunity Engine data model, cost observability, and Mission Control V2.
4. **Phase 1B is now functionally proven.** The isolated lab proves install/start, model/provider, session continuity, memory, skill loading, delegation, isolated cron/gateway execution, plugin integration, deterministic Nexus capability lookup, and governance boundaries. The upstream Codex auth path is still unconfigured on this machine, but the local fallback path works.
5. **Phase 5 now has a canonical opportunity foundation.** Existing business opportunities, research intake, Hermes recommendation surfaces, and Alpha artifacts are reused through a deterministic canonical model with dedupe, scoring, compact AI synthesis, and a safe pilot path. Cost accounting is now normalized to USD per 1,000,000 tokens with explicit provenance.
6. **Phase 6 has been audited without adding a new agent.** Alpha already owns external intelligence: live research, scoring, memory, provider routing, URL review, SEO/money opportunity work, trading research, and research-file handling. The open-source scout is a workflow attached to Alpha, not a new persistent identity.
7. **Phase 6B now proves the deterministic external intelligence path end to end.** A bounded public-source scout audited Nexus first, normalized four candidate repositories from eight collected source records, collapsed duplicate content by hash, and handed a canonical opportunity-engine input forward with zero AI executions and zero token cost.
8. **Phase 7 now has an evidence-driven creative lab foundation.** Creative direction remains a skill, not a persistent agent. The lab audited the repo’s existing creative, marketing, and design surfaces, produced three distinct territories, kept provenance and build-spec constraints intact, and ran a zero-token safe pilot instead of publishing anything.
4. **Environment note:** `E2E_PERSONA_*` / `E2E_ADMIN_*` credentials and search API keys are absent. This is ENV_BLOCKED_E2E — it does not block the sprint.

## Process classification (41 entries)
- KEEP_PYTHON 23 · KEEP_LANGGRAPH 3 · KEEP_TEMPORAL 1 · WRAP_WITH_HERMES 2 · AI_ASSISTED 5 · REPLACE_ONLY_IF_PROVEN 1 · SIMPLIFY 1 · DEPRECATE_LATER 2 · PROTECTED/no-op 3.
- No deterministic process is classified REPLACE.

## Resume point
Next: **mission_control_visibility**. The loop runtime now exists for `system_health_loop` and `opportunity_discovery_loop`, with bounded state, ledgering, zero-token no-change exits, deterministic-first AI gating, and normalized per-million-token cost accounting. The opportunity engine layer is canonical and read-only over existing governed sources, Alpha has been audited as the persistent external-intelligence arm, the deterministic open-source scout proof is now complete, and the Creative Lab foundation now reuses existing creative surfaces without introducing a new persistent agent.

## Protected invariants carried forward
Client Portal V2, classic `/client`, Supabase/RLS, governance, approvals, work orders, model router, production Telegram, Alpha PII isolation, client vault separation, all KEEP_PYTHON processes.
