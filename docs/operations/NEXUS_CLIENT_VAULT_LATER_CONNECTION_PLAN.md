# Nexus Client Vault — Later Connection Plan

The production Client Vault connection is a **manual, separately approved** step that happens later —
not in this task. Until then, `connection_status = not_connected_by_design` and only the mock adapter
is used.

## Preconditions before connecting a live vault

1. Nexus engine is stable.
2. AI access boundaries are verified (`verify_ai_department_access.py` green).
3. Client Vault contract is proven (`verify_client_vault_contract.py` green).
4. Hermes raw-client-data blocking is verified.
5. Credit Specialist Supabase-only contract is verified.

## Connection steps (future)

1. Choose a backend: separate Supabase project / separate schema / self-hosted Supabase / plain
   Postgres vault / other.
2. Provision credentials in secret storage (never committed; never in `.env` in git).
3. Implement a `LiveClientVaultAdapter` satisfying `ClientVaultAdapter`.
4. Flip the factory only behind an explicit, approved flag + audit logging enabled.
5. Run the full verification suite against the live adapter in a staging tenant first.

## Hard rules (now)

- No second live Supabase project.
- No real Client Vault credentials.
- No real client data.
- Mock adapter only.
