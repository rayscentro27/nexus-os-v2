---
name: nexus-credit-readiness
description: Credit readiness review skill for governed Nexus client-scoped reads.
status: DRAFT
lifecycle: DRAFT
---

# Purpose

Review client-scoped readiness without exposing unnecessary PII.

# Activation Criteria

- Funding readiness, credit readiness, or client-scoped review is requested.

# Inputs

- Email or client_id
- Client-scoped readiness status
- Client profile summary

# Procedure

1. Verify the request is client-scoped.
2. Read only the needed profile/readiness data.
3. Preserve the tenant and PII boundaries.

# Allowed Tools

- nexus_funding_readiness_summary
- nexus_credit_summary
- nexus_client_summary

# Deterministic-First Rules

- Prefer bounded profile/readiness reads over broad synthesis.

# Evidence Requirements

- Tenant scope
- PII classification
- Provenance

# Verification

- Confirm the response does not exceed the requested scope.

# Output Format

- Client readiness summary
- Next action

# Escalation

- Escalate when client identity is missing or ambiguous.

# Prohibited Actions

- Writes
- Unscoped client data access
