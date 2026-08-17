---
name: nexus-credit-result-verification
description: Verification skill for bounded credit-result evidence checks.
status: DRAFT
lifecycle: DRAFT
---

# Purpose

Verify credit-related results from governed, bounded reads only.

# Activation Criteria

- A credit result, credit report, or readiness output needs verification.

# Inputs

- Client-scoped evidence
- Readiness summary
- Provenance

# Procedure

1. Confirm tenant scope.
2. Read the smallest relevant evidence set.
3. Reconcile the result against the source data.

# Allowed Tools

- nexus_credit_summary
- nexus_client_summary
- nexus_capability_lookup

# Deterministic-First Rules

- Verify the evidence before forming any conclusion.

# Evidence Requirements

- Source capability
- Tenant scope
- PII classification

# Verification

- Confirm the result matches the evidence.

# Output Format

- Verified result
- Evidence note

# Escalation

- Escalate on ambiguity or missing evidence.

# Prohibited Actions

- Writes
- Claiming unsupported credit outcomes
