---
name: nexus-opportunity-director
description: Deterministic-first opportunity discovery and scoring skill.
status: DRAFT
lifecycle: DRAFT
---

# Purpose

Evaluate and score opportunities without bypassing deterministic data sources.

# Activation Criteria

- Opportunity discovery, validation, or ranking is requested.

# Inputs

- Opportunity description
- Evidence
- Research results
- System and revenue context

# Procedure

1. Gather bounded evidence.
2. Score with deterministic math where possible.
3. Separate known, inferred, and unverified claims.
4. Recommend the smallest safe next step.

# Allowed Tools

- nexus_revenue_status
- nexus_research_status
- nexus_capability_lookup

# Deterministic-First Rules

- Score with rules and evidence before any narrative synthesis.

# Evidence Requirements

- Evidence list
- Confidence / status labels
- Score rationale

# Verification

- Check that the recommendation follows from the evidence.

# Output Format

- Opportunity summary
- Score
- Next action

# Escalation

- Escalate when the evidence is too weak for a recommendation.

# Prohibited Actions

- Fabrication
- Writes
- Public publishing
