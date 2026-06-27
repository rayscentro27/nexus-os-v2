# Hermes Redaction Policy

- ok: True

## Proofs
- forbidden_fields_stripped: True
- sanitized_set_is_pii_free: True
- hermes_blocked_from_raw_credit_report: True
- hermes_blocked_from_smartcredit_file: True

## Redaction example
- stripped: account_number, address, bank_statement, dob, full_client_name, raw_credit_report, raw_letter, smartcredit_file, ssn
- kept: ray_review_needed_count, stuck_clients_count
