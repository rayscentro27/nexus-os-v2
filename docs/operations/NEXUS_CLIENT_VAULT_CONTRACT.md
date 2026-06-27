# Nexus Client Vault Contract

Ray approved the Client Vault architecture, but the real vault is **NOT connected yet**. This task
ships the contract + mock adapter only.

Source: `src/config/clientVaultContract.ts`, `src/lib/clientVaultAdapter.ts`,
`src/lib/mockClientVaultAdapter.ts`.

## Status (by design)

- `connection_status: not_connected_by_design`
- `adapter_in_use: mock`
- `second_supabase_connected: false`
- `real_credentials_present: false`
- `real_client_data_present: false`

`getClientVaultAdapter()` always returns the mock adapter and throws if anyone attempts a live
connection — there is no live implementation in v1.

## Adapter interface

`ClientVaultAdapter` covers: client profiles, credit report metadata, credit score snapshots,
business profile + setup items, proof uploads, letter packets, mailing records, workflow tasks,
reminder tasks, funding readiness summaries, affiliate attribution, consent events, audit events,
and a sanitized signal export (the only path toward Hermes).

## Supported future backends

`separate_supabase_project`, `separate_schema`, `self_hosted_supabase`, `plain_postgres_vault`,
`other_backend`. See
[NEXUS_CLIENT_VAULT_LATER_CONNECTION_PLAN.md](NEXUS_CLIENT_VAULT_LATER_CONNECTION_PLAN.md).

Verify: `python3 scripts/client_vault/verify_client_vault_contract.py --dry-run --json`.
