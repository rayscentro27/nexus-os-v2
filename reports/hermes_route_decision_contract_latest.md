# Hermes RouteDecision Contract

Every Hermes message now receives one immutable RouteDecision before context is assembled. The decision controls activation level, domain, intent, memory, retrieval, model, diagnostics, and action policy.

The priority router is deterministic: safety; trace/source; cost/model status; casual; capability; process/settings/reports; approval preparation; explicit inventory retrieval; selection follow-up; revenue; local reasoning; model reasoning; clarification.

Context construction is deny-by-default. Trace routes receive only the last trace. Selection routes require an explicit marker or named match. Revenue receives long-term business context without stale selection. Inventory retrieves before reasoning. Routes with forbidden model or no retrieval cannot access those facilities.

Contract integrity assertions reject inconsistent policy combinations at creation time.
