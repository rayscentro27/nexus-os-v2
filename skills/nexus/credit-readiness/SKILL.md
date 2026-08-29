---
name: credit-readiness
version: 1.0.0
owner: nexus
status: READY_FOR_SYNTHETIC
authority_class: internal_review
side_effect_class: local_reports
default_profile: nexusworker
model_policy: GENERAL_REASONING
allowed_executors:
receipt_required: true
---
# Purpose
Assess synthetic credit-readiness inputs and identify documentation gaps.
# When To Use
Only with synthetic or explicitly authorized internal data.
# When Not To Use
Never mutate client records or submit applications.
# Inputs
Synthetic readiness facts and freshness.
# Required Context
Data classification and review authority.
# Data Sources
Approved Nexus fixtures only.
# Authority Requirements
Internal review authority.
# Dependencies
No external credit action.
# Allowed Python Executors
None until a dedicated certified executor exists.
# Model Routing
GENERAL_REASONING advisory only.
# Worker / Profile
NEXUS_FUNDING_WORKER / `nexusworker`.
# Procedure
Normalize, identify gaps, recommend review.
# Output Contract
Gap list with confidence and evidence.
# Validation
Schema and freshness checks.
# Side-Effect Validation
Local artifact only.
# Receipt Requirements
Receipt required for every run.
# Retry Policy
No retry on ambiguous financial data.
# Handoff Policy
Ray review work item.
# Failure Modes
Missing or stale facts.
# Escalation Rules
Mark NOT_PROVEN.
# Security Boundaries
No PII leakage or financial submission.
# Examples
Use the synthetic credit fixture.
