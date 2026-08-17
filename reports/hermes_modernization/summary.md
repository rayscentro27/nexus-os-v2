# Nexus Hermes Modernization — Summary

**Status:** Phase 0 (Audit) complete · Checkpoint 1 heads to `origin/main`
**Baseline HEAD:** `2aab745` · Client Portal V2: COMPLETE / PROTECTED

## What Phase 0 established

1. **The system is already deterministic-first.** Every enabled schedule in the 70-entry automation registry is `internal_safe`; model routing is a deterministic policy layer; approvals are single-use with TTL; work orders are an idempotency-keyed state machine; media downloads, live Stripe, live trading, and public publishing are all disabled/approval-gated by policy.
2. **AI is already confined.** Only 4 processes make model calls (Hermes front brain, Nova, Alpha research, LiteLLM adapter), all gated and redacted. LangGraph exists as 3 thin graphs behind flags. No LangGraph exists for credit/outcome/funding reasoning — those stay deterministic (correct).
3. **The offer-engine target is minimally additive.** The biggest genuine gaps are: a Python capability registry (only a nascent per-agent registry exists), a Hermes skills concept, a loop framework, an Opportunity Engine data model (only partial tables exist), cost observability, and Mission Control V2.
4. **Environment note:** `E2E_PERSONA_*` / `E2E_ADMIN_*` credentials and search API keys are absent. This is ENV_BLOCKED_E2E — it does not block the sprint.

## Process classification (41 entries)
- KEEP_PYTHON 23 · KEEP_LANGGRAPH 3 · KEEP_TEMPORAL 1 · WRAP_WITH_HERMES 2 · AI_ASSISTED 5 · REPLACE_ONLY_IF_PROVEN 1 · SIMPLIFY 1 · DEPRECATE_LATER 2 · PROTECTED/no-op 3.
- No deterministic process is classified REPLACE.

## Resume point
Next: **Nexus Python Capability Registry** (`reports/hermes_modernization/python_capability_registry.md`), building on `scripts/nexus_agent_platform/capabilities/registry.py` as a deterministic capability inventory (name, module, input/output contract, cost class, side-effecting flag, risk class, tenant scope, timeout, test status). Then the isolated Hermes upstream lab.

## Protected invariants carried forward
Client Portal V2, classic `/client`, Supabase/RLS, governance, approvals, work orders, model router, production Telegram, Alpha PII isolation, client vault separation, all KEEP_PYTHON processes.