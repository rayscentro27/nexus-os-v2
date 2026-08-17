# Nexus Hermes Modernization — Summary

**Status:** Phase 1A complete · Phase 1B isolated upstream Hermes compatibility lab added · Checkpoint 3 pending push
**Baseline HEAD:** `68b037d` · Client Portal V2: COMPLETE / PROTECTED

## What Phase 0 established

1. **The system is already deterministic-first.** Every enabled schedule in the 70-entry automation registry is `internal_safe`; model routing is a deterministic policy layer; approvals are single-use with TTL; work orders are an idempotency-keyed state machine; media downloads, live Stripe, live trading, and public publishing are all disabled/approval-gated by policy.
2. **AI is already confined.** Only 4 processes make model calls (Hermes front brain, Nova, Alpha research, LiteLLM adapter), all gated and redacted. LangGraph exists as 3 thin graphs behind flags. No LangGraph exists for credit/outcome/funding reasoning — those stay deterministic (correct).
3. **The offer-engine target is still minimally additive.** The current gap list has advanced to the isolated upstream Hermes compatibility lab, plugin boundary, skills framework, loop framework, Opportunity Engine data model, cost observability, and Mission Control V2.
4. **Phase 1B is not fully certified yet.** The isolated lab now proves install/start, model/provider, session continuity, memory, skill loading, delegation, plugin integration, deterministic Nexus capability lookup, and governance boundaries; cron remains partial in the sandbox because the gateway is not running.
4. **Environment note:** `E2E_PERSONA_*` / `E2E_ADMIN_*` credentials and search API keys are absent. This is ENV_BLOCKED_E2E — it does not block the sprint.

## Process classification (41 entries)
- KEEP_PYTHON 23 · KEEP_LANGGRAPH 3 · KEEP_TEMPORAL 1 · WRAP_WITH_HERMES 2 · AI_ASSISTED 5 · REPLACE_ONLY_IF_PROVEN 1 · SIMPLIFY 1 · DEPRECATE_LATER 2 · PROTECTED/no-op 3.
- No deterministic process is classified REPLACE.

## Resume point
Next: **Phase 2 - nexus-hermes-plugin** after the compatibility lab follow-up work is finalized. Phase 1B now has an isolated upstream Hermes lab at `scripts/nexus_agent_platform/hermes_lab/upstream_compatibility.py` and a report at `reports/hermes_modernization/upstream_compatibility.md`.

## Protected invariants carried forward
Client Portal V2, classic `/client`, Supabase/RLS, governance, approvals, work orders, model router, production Telegram, Alpha PII isolation, client vault separation, all KEEP_PYTHON processes.
