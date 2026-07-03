# Hermes Alpha Brain-First Architecture

## Separation decision

Hermes Alpha is a distinct research and experiment-planning agent. Nexus Hermes remains the operator for Nexus OS, GoClear, clients, readiness, Ray Review, system status, and approved local processes. Mixing them would let unreviewed public research compete with operational truth and client-safe controls.

Phase 1 deliberately excludes Supabase because Alpha must first prove its reasoning contract, lane routing, structured output, safety gates, and provider independence. A database would create accidental source authority and coupling before the brain is stable.

## Mission and source order

Alpha turns Ray's objectives and allowed research into scored business opportunities, draft marketing assets, trading research plans, reports, and conversation-only Ray Review proposals.

1. Ray's objective
2. Alpha brain instructions
3. Model reasoning
4. Public research or uploaded documents when enabled
5. Alpha local memory
6. Opportunity/trading/marketing scoring frameworks
7. Backtest/demo results when available later
8. Recommendation/report/proposal output

Supabase is not in this order and must never become Alpha source authority.

## Brain v1 graph

`classify_objective → select_lane → gather_context → score_or_structure → create_recommendation → create_report_or_proposal → write_alpha_memory → return_response`

Lanes: research intake, business opportunity, marketing asset, affiliate offer, trading research, and general strategy. Every response returns answer, lane, confidence, assumptions, next experiment, risk, recommendation, Ray Review draft option, source mode, and `noSupabaseUsed: true`.

## Memory

Phase 1 memory is process-local and resettable. Store objective, lane, assumptions, recommendation, source mode, and timestamp—not secrets, credentials, client data, or raw protected documents. Later memory may use append-only local files with retention limits. Letta/MemGPT-style working, episodic, and promoted memory is a conceptual reference; autonomous self-editing is excluded.

## Provider/model design

The provider interface returns text, provider, cost, and external-call status. Default is mock, external calls are forbidden, and cost is zero. Future adapters: Ollama local, Ollama cloud, OpenRouter backup, and a hosted/self-hosted provider. Provider choice cannot change safety or source order.

## Desks and labs

- Business Opportunity Desk: score demand, revenue, speed, test cost, fit, compliance, affiliate potential, and next experiment.
- Marketing/Asset Studio: draft audience-specific campaigns, landing pages, newsletters, social posts, and creative prompts; never send or publish.
- Trading Research Lab: specify and score strategies, design backtests, review risk and stability, and rank evidence; never execute trades.
- Future Oanda demo: practice-only execution behind explicit flags, policy limits, receipts, kill switch, strategy ID, and Ray Review. Not connected now.
- Future Research Vault: curated read-only evidence adapter, no client data or broad table access, never source authority. Not connected now.

## Phase 1 restrictions

No database client/import/env, Research Vault, Nexus/client context, production calls, broker connection, demo/live trade, email, publish, charge, service key, secret, scheduler, or external model. The scaffold is disabled, mock/offline, zero-cost, and tested statically.
