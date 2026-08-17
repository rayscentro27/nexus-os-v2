---
name: nexus-funding-readiness
description: Funding readiness skill for bounded tenant-scoped Nexus reads.
status: DRAFT
lifecycle: DRAFT
---

# Purpose

Review funding readiness with tenant scope and PII protections intact.

# Activation Criteria

- Funding readiness or funding access is requested for a specific client.

# Inputs

- Email or client_id
- Readiness summary
- Client profile

# Procedure

1. Require a tenant-scoped identifier.
2. Read only the relevant readiness and profile data.
3. Preserve PII boundaries.

# Allowed Tools

- nexus_funding_readiness_summary
- nexus_client_summary
- nexus_credit_summary

# Deterministic-First Rules

- Do not expand into unrelated client data.

# Evidence Requirements

- Tenant scope
- PII classification
- Provenance

# Verification

- Confirm the readiness statement matches the source data.

# Output Format

- Funding readiness summary
- Next step

# Escalation

- Escalate when the identity is missing or the result is ambiguous.

# Prohibited Actions

- Writes
- Unscoped client access
