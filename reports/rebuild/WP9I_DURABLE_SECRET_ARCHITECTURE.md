# WP9I durable secret architecture

## Implemented path

- Existing Mac OpenRouter credential reused; no rotation and no new provider.
- Mac copy stored in macOS Keychain service `nexus-openrouter-provider`.
- Existing Oracle Hermes API credential remains in the existing Oracle
  mode-600 service environment.
- Existing OpenRouter credential is stored only in the existing Oracle
  Hermes data volume profile/service environment with mode 600 permissions.
- Mac bridge API credential is stored in Keychain service
  `nexus-oracle-hermes-api`; the bridge reads it at runtime and never writes,
  logs, or places it in process arguments.
- `scripts/nexus_agent_platform/bridge/oracle_hermes.py` now supports the
  Keychain fallback and an explicit model environment override.

## Verification

After restarting the existing `nexus-hermes-0206` service, the protected API
continued to report Hermes `0.20.6`. The API returned HTTP 200 and the exact
sentinel `ORACLE_NOVA_PERSISTENCE_OK`. The Mac bridge then returned HTTP 200
health and `ORACLE_BRIDGE_MODEL_OK` through the Keychain-resolved credential.

`DURABLE_SECRET_STORE=MAC_KEYCHAIN;ORACLE_STRICT_PERMISSIONS`
`DURABLE_SECRET_INJECTION=PASS`
`SECRET_AT_REST_PROTECTION=PASS`
`SECRET_LOG_REDACTION=PASS`

The provider model is an existing OpenRouter `:free` route. Auxiliary paid
fallback is disabled in the Nova profile to preserve the zero-new-spend gate.
