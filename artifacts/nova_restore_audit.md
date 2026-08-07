# Nova Brain Restoration Audit

## Original Nova Message Path (commit 984a454)

```
classify_intent → handle_utility → build_context → generate_response → validate_output → compose_output
```

- No Supabase capability interception
- No imports from nova_supabase
- Model always saw the full user message
- SOUL was purely conversational — no capability descriptions
- No conditional routing around the model

## Regressed Nova Message Path (commit 4787077)

```
classify_intent → handle_utility → check_supabase → (conditional) → build_context → generate_response → validate_output → compose_output
```

- `check_supabase` node runs BEFORE the model
- Imports from nova_supabase for trigger detection and capability execution
- When trigger matches (e.g., "how many clients"), model is bypassed entirely
- Conditional edge routes to compose_output, skipping build_context and generate_response
- SOUL contains capability descriptions that compete with conversational personality

## Exact Regression Point

Commit bc3820d: `feat(nova): wire governed Supabase read access into Nova graph`

This commit added:
- `_check_supabase_capability()` node function
- `check_supabase` graph node
- Conditional edge after check_supabase
- Imports from nova_supabase

## Hermes/Shared Brain Dependencies Found

- `nexus_agent_platform.connectors.nova_supabase` — capability detection, execution, response generation
- `nexus_agent_platform.capabilities.shared` — execute_shared_capability, permission profiles
- `_MODE_PATTERNS` — Hermes-style intent classification (TIME_REQUEST, ARITHMETIC, etc.)
- SOUL capability descriptions — injected capability awareness

## Trigger-Pattern Behavior Found

`get_nova_capabilities()` returns triggers that match BEFORE the model:
- "how many clients" → get_client_count → canned response
- "client count" → get_client_count → canned response
- "find user" + "@" → resolve_user_identity_by_email → canned response

These bypass Nova's original conversational comprehension.

## Business-Context Changes Found

- SOUL lost "If asked about Nexus internals, explain you are Nova — a conversational agent"
- SOUL gained capability descriptions that dominate the system prompt
- No GoClear business context in SOUL
- No revenue-generation advisory context

## Regression Point Summary

The `check_supabase` node is the sole cause of conversational regression. It intercepts messages before Nova's model can interpret them naturally. When a trigger matches, the model never sees the message.

## Files Involved

- `scripts/nexus_agent_platform/agents/nova.py` — graph, SOUL, capability check
- `scripts/nexus_agent_platform/connectors/nova_supabase.py` — capability handlers
- `scripts/nexus_agent_platform/capabilities/shared.py` — shared execution layer

## Code Paths Being Retained

- Shared Supabase session management
- Canonical client-count handler
- Identity resolution handler
- Provenance envelope
- Safe projection
- Permission enforcement (read-only)
- Audit logging

## Code Paths Being Removed

- `check_supabase` graph node (intercepts before model)
- Capability trigger patterns (keyword matching)
- Pre-model capability execution
- Conditional edge routing around model
- Capability response generation (canned responses)
- SOUL capability descriptions

## Security Functionality Being Preserved

- Read-only access enforcement
- Write detection and denial
- Credential isolation
- Safe result envelopes
- Provenance tracking
- Audit logging
