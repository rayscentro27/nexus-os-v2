# Nexus Future CRM Evaluation Policy

No CRM repo is integrated in the current work. The following may be **evaluated later only** and must
not be installed, imported, or wired until the preconditions below are met:

- Twenty
- Relaticle
- Atomic CRM
- Open Mercato
- NextCRM
- crm-logic

## Preconditions before any CRM evaluation

1. Nexus engine is stable.
2. AI access boundaries are verified (`scripts/ai_access/verify_ai_department_access.py` green).
3. Client Vault contract is proven (`scripts/client_vault/verify_client_vault_contract.py` green).
4. Hermes raw-client-data blocking is verified
   (`scripts/ai_access/generate_hermes_redaction_report.py` green).
5. Credit Specialist Supabase-only contract is verified
   (`scripts/ai_access/generate_credit_specialist_contract_report.py` green).

## Rules

- Evaluation only — no integration, no dependency added, no data shared until a separate, approved
  task.
- Any future CRM must sit behind the same AI access boundaries and the Client Vault contract; it
  must never receive raw client data outside the vault adapter and audit logging.
