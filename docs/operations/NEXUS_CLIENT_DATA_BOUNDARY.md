# Nexus Client Data Boundary

Defines what data leaves the Client Vault and to whom. Source: `nexusClientDataSensitivityPolicy.ts`.

## Categories

- **Sanitized / aggregate** (`sanitized_signal`, `aggregate_metric`, `stage_count`,
  `workflow_status_internal`) — Hermes-safe; no PII.
- **Private vault-only** (`client_name`, `client_contact`, `address`, `dob`, `ssn`,
  `account_number`, `creditor_account_detail`, `bank_statement`, `raw_credit_report`,
  `smartcredit_file`, `credit_score_raw`, `raw_letter`, `funding_document`,
  `client_consent_record`) — reachable ONLY through the Client Vault adapter; never for Hermes or
  internet-enabled tools.

## Rules

- Private client data is `vault_only` and never crosses to Hermes or any internet tool.
- Internet-enabled tools can never reach Client Vault data (hard separation).
- Specialist AIs read private data only through the adapter (mock in v1).
- Client-facing recommendations remain approval-gated.
