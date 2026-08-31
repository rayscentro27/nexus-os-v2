# Nova Model Strategy Audit

## Current strategy

Nova currently selects one configured `HERMES_NOVA_MODEL` for final generation
and one configured planner model, both through the Nexus-owned adapter; the
runtime has historically used `openai/gpt-4o-mini` through direct OpenRouter.
The direct path does not use Hermes's native model loop, native provider
fallback, or native tool continuation.

## Recommended future strategy (not implemented)

1. **Level 1 — simple conversation:** current approved low-cost model/path.
2. **Level 2 — business reasoning:** stronger approved model or provider effort
   option when available, with the same Nova identity and context.
3. **Level 3 — high-consequence strategy/economics:** stronger approved model,
   explicit evidence, and optional human/Alpha challenge. No automatic paid
   invocation.

The selection mechanism should remain cost-aware and capability-bound. It should
not become a phrase router or a mandatory multi-model chain. Local/private
Ollama is a plausible low-cost background summarizer, first-pass analyst, or
ensemble reference, but it should not replace Nova's primary conversational
model without a separate quality/provenance proof.

