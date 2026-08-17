---
name: nexus-operator
description: Governed Nexus operator skill for deterministic-first status, approvals, and safe execution routing.
status: DRAFT
lifecycle: DRAFT
---

# Purpose

Operate Nexus with read-only first principles and explicit evidence.

# Activation Criteria

- Nexus status, process status, runtime status, or approvals are being reviewed.
- A deterministic capability already exists for the request.

# Inputs

- User request
- Nexus capability registry lookup
- Current runtime/process/approval state

# Procedure

1. Look up the relevant Nexus capability first.
2. Prefer deterministic reads over model synthesis.
3. Use governed read-only tools only.
4. Surface provenance and state boundaries explicitly.

# Allowed Tools

- nexus_capability_lookup
- nexus_system_status
- nexus_process_status
- nexus_runtime_status
- nexus_pending_approvals

# Deterministic-First Rules

- Do not use model reasoning for a request already covered by a deterministic capability.
- Do not infer execution from configuration.

# Evidence Requirements

- Capability metadata
- Source requirement
- Provenance

# Verification

- Confirm the answer is read-only and traceable to a governed capability.

# Output Format

- Short operational summary
- Relevant capability evidence

# Escalation

- Escalate only when a write, approval, or missing evidence boundary is hit.

# Prohibited Actions

- Writes
- Shell execution
- SQL execution
- Unrestricted filesystem access
