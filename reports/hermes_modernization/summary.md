# Nexus Hermes Modernization — Summary

**Status:** Phase 1A complete · Phase 1B isolated upstream Hermes compatibility lab proven · Phase 2 plugin boundary and initial skills added · Phase 3B skill / role reconciliation complete · Phase 4 loop runtime complete · Phase 5 opportunity engine foundation complete · Phase 5B cost accounting verified · Phase 6 Alpha external intelligence audit started
**Baseline HEAD:** `bc2f622` · Client Portal V2: COMPLETE / PROTECTED

## What Phase 0 established

1. **The system is already deterministic-first.** Every enabled schedule in the 70-entry automation registry is `internal_safe`; model routing is a deterministic policy layer; approvals are single-use with TTL; work orders are an idempotency-keyed state machine; media downloads, live Stripe, live trading, and public publishing are all disabled/approval-gated by policy.
2. **AI is already confined.** Only 4 processes make model calls (Hermes front brain, Nova, Alpha research, LiteLLM adapter), all gated and redacted. LangGraph exists as 3 thin graphs behind flags. No LangGraph exists for credit/outcome/funding reasoning — those stay deterministic (correct).
3. **The offer-engine target is still minimally additive.** The current gap list has advanced to the isolated upstream Hermes compatibility lab, plugin boundary, skills framework, loop framework, Opportunity Engine data model, cost observability, and Mission Control V2.
4. **Phase 1B is now functionally proven.** The isolated lab proves install/start, model/provider, session continuity, memory, skill loading, delegation, isolated cron/gateway execution, plugin integration, deterministic Nexus capability lookup, and governance boundaries. The upstream Codex auth path is still unconfigured on this machine, but the local fallback path works.
5. **Phase 5 now has a canonical opportunity foundation.** Existing business opportunities, research intake, Hermes recommendation surfaces, and Alpha artifacts are reused through a deterministic canonical model with dedupe, scoring, compact AI synthesis, and a safe pilot path. Cost accounting is now normalized to USD per 1,000,000 tokens with explicit provenance.
6. **Phase 6 has been audited without adding a new agent.** Alpha already owns external intelligence: live research, scoring, memory, provider routing, URL review, SEO/money opportunity work, trading research, and research-file handling. The open-source scout is a workflow attached to Alpha, not a new persistent identity.
4. **Environment note:** `E2E_PERSONA_*` / `E2E_ADMIN_*` credentials and search API keys are absent. This is ENV_BLOCKED_E2E — it does not block the sprint.

## Process classification (41 entries)
- KEEP_PYTHON 23 · KEEP_LANGGRAPH 3 · KEEP_TEMPORAL 1 · WRAP_WITH_HERMES 2 · AI_ASSISTED 5 · REPLACE_ONLY_IF_PROVEN 1 · SIMPLIFY 1 · DEPRECATE_LATER 2 · PROTECTED/no-op 3.
- No deterministic process is classified REPLACE.

## Resume point
Next: **alpha_external_intelligence_pipeline** after the audit checkpoint. The loop runtime now exists for `system_health_loop` and `opportunity_discovery_loop`, with bounded state, ledgering, zero-token no-change exits, deterministic-first AI gating, and normalized per-million-token cost accounting. The opportunity engine layer is canonical and read-only over existing governed sources, and Alpha has been audited as the persistent external-intelligence arm.

## Protected invariants carried forward
Client Portal V2, classic `/client`, Supabase/RLS, governance, approvals, work orders, model router, production Telegram, Alpha PII isolation, client vault separation, all KEEP_PYTHON processes.
