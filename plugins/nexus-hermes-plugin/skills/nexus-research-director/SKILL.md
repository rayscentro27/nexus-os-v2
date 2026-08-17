---
name: nexus-research-director
description: Research intake and evidence synthesis skill for governed Nexus discovery.
status: DRAFT
lifecycle: DRAFT
---

# Purpose

Route research requests through bounded, governed reads first.

# Activation Criteria

- The question asks for evidence, reports, recent activity, or study findings.

# Inputs

- User question
- Report index
- Recent activity
- Study snapshot or business model summary

# Procedure

1. Identify the narrowest governed read that answers the request.
2. Pull only bounded evidence.
3. Preserve source commit and freshness.
4. Summarize without inflating the data.

# Allowed Tools

- nexus_research_status
- nexus_capability_lookup
- nexus_system_status

# Deterministic-First Rules

- Prefer report index, latest reports, and study summaries before any AI synthesis.

# Evidence Requirements

- Source ref
- Source commit
- Generated at / freshness

# Verification

- Confirm the answer is traceable to a bounded source.

# Output Format

- Bounded evidence summary
- Provenance note

# Escalation

- Escalate when the data is unavailable or incomplete.

# Prohibited Actions

- Writes
- Raw data dumps
- PII exposure
