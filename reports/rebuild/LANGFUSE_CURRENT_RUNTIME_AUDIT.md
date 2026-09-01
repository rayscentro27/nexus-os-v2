# Langfuse current runtime audit

Langfuse is attached only to the Hermes-native Nova Telegram path. The legacy
Agent Platform adapter remains reusable observability code, but its brain,
router, and execution graph are not invoked for Nova.

Active path: `scripts/nova/nova_telegram_worker.py` →
`scripts/nova/nova_hermes_shadow.py` → profile-local Hermes/MCP/Web/Alpha →
Telegram delivery. Langfuse is fail-open and never controls execution.
