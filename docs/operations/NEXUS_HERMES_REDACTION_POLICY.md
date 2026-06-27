# Nexus Hermes Redaction Policy

Hermes must not directly access raw client data. Source: `src/lib/hermesClientDataRedaction.ts`,
`src/lib/sanitizedClientSignals.ts`, `src/config/hermesSafeClientSignalPolicy.ts`.

## Hermes may access

Sanitized client metrics, aggregated workflow signals, stage counts, stuck-client counts, affiliate
opportunity counts, funding readiness delay summaries, revenue risk summaries, Ray-Review-needed
counts.

## Hermes must NOT access

Full client names (unless explicitly policy-allowed), full credit reports, SmartCredit files/imports,
SSNs, DOBs, addresses, account numbers, creditor account details, bank statements, raw letters,
private funding documents.

## Enforcement

`redactForHermes()` strips any forbidden/PII-looking key (fail closed). `assertSignalsArePiiFree()`
confirms a signal object exposes only allow-listed keys. `buildSanitizedClientSignals()` produces the
only structure Hermes consumes.

## Hermes-safe signal examples

- "4 clients are stuck at credit report upload."
- "2 clients selected AnnualCreditReport.com and have no score."
- "5 clients are missing business bank accounts."
- "3 clients have letters ready but no mailing proof."
- "1 client is nearly funding-ready but has high utilization."
- "Estimated commission opportunity delayed: $X."

Verify: `python3 scripts/ai_access/generate_hermes_redaction_report.py --dry-run --json`.
