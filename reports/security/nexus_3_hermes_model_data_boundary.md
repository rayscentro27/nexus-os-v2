# Nexus 3 Hermes Model Data Boundary

Generated: 2026-07-20

## Browser

The browser may send only the user message, bounded visible conversation history, and safe page context through the Supabase Function client. It may not send provider keys, service-role credentials, tenant overrides, approval state, or execution authority.

## Supabase Edge Function

`supabase/functions/hermes-chat/index.ts` owns the OpenRouter call and the governed tool bridge. Provider credentials are read only from `Deno.env`.

The Edge Function sends OpenRouter:

- stable Hermes identity and policy context,
- bounded safe dynamic context,
- bounded sanitized visible conversation history,
- current Ray message,
- safe tool names/descriptions/input schemas,
- sanitized tool result summaries when a tool is approved.

The Edge Function does not send OpenRouter:

- API keys,
- Supabase service-role keys,
- SSNs,
- full credit reports,
- bank details,
- raw client documents,
- tenant override authority,
- hidden chain-of-thought.

## OpenRouter

OpenRouter receives only sanitized conversation context and tool metadata/results. It may propose a tool through the decision contract, but it cannot execute a tool or approve itself.

## Supabase

Supabase remains authoritative for Nexus facts and operational state. The first bridge performs aggregate and report-safe reads only. Client aggregate output is count-level and does not include names, addresses, SSNs, credit report data, bank details, or raw documents.

## Alpha

Alpha is unchanged. No Supabase access or client PII access is granted to Alpha in this phase.

## Department Operations

The Department Operations migration remains separate and unapplied by this phase. Hermes department status must label the current department evidence as `SYNTHETIC_READ_MODEL` until durable production queue persistence is active.

## Security Result

Local scan of changed paths found no new provider key, service-role key, or frontend-exposed OpenRouter secret. Existing repository reports contain redacted historical environment references and were not modified as part of this bridge.
