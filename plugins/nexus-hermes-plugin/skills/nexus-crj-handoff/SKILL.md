---
name: nexus-crj-handoff
description: CRJ handoff and governed evidence transfer skill.
status: DRAFT
lifecycle: DRAFT
---

# Purpose

Prepare bounded handoff material for CRJ review without leaking extra data.

# Activation Criteria

- A CRJ handoff or evidence transfer is requested.

# Inputs

- Approved evidence
- Read-only summaries
- Provenance

# Procedure

1. Select only the relevant evidence.
2. Keep the output bounded.
3. Preserve provenance and scope.

# Allowed Tools

- nexus_business_foundation_summary
- nexus_revenue_status
- nexus_capability_lookup

# Deterministic-First Rules

- Do not add unsupported interpretation.

# Evidence Requirements

- Source refs
- Freshness
- Scope

# Verification

- Confirm the handoff is limited to approved evidence.

# Output Format

- Handoff summary
- Evidence appendix

# Escalation

- Escalate when the evidence is incomplete.

# Prohibited Actions

- Writes
- Broad data export
