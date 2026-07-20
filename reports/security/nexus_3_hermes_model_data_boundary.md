# Nexus 3 Hermes Model Data Boundary

Generated: 2026-07-20

## Letta

Letta may receive Hermes persona, Ray conversational preferences, sanitized recent conversation, active objectives, and durable conversational summaries.

Letta must not receive Supabase credentials, raw client PII, unredacted customer documents, hidden chain-of-thought, or authorization authority.

Current state: runtime not configured.

## OpenRouter

OpenRouter may receive sanitized user messages, Letta-provided conversational context, approved tool schemas, and approved tool results.

OpenRouter must not receive provider keys in the browser, Supabase credentials, raw client PII, unredacted internal documents, or authority to execute tools.

Current state: server key missing.

## Supabase

Supabase remains the authoritative store for Nexus facts, operational status, reports, client aggregates, approvals, provenance, audit records, and cost records.

Supabase must not store hidden chain-of-thought or provider API keys in normal tables.

## Browser

The browser may send the user message, conversation ID, and sanitized page context to the server endpoint.

The browser may not submit provider keys, Letta keys, tenant overrides, role overrides, tool approval, or agent authority.

## Logs

Logs may contain sanitized trace IDs, provider/model names, token counts, costs, decision types, and tool names. Logs must not contain secrets, raw PII, or hidden reasoning.

## Boundary Decision

The branch preserves the data boundary. No model-first runtime is certified active while OpenRouter and Letta are unconfigured.
