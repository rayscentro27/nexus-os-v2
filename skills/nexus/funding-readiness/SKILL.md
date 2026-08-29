---
name: funding-readiness
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
Combine synthetic credit and business evidence into a funding-readiness recommendation.
# When To Use
For internal planning and Ray review.
# When Not To Use
Never apply, borrow, pay, or mutate production client data.
# Inputs
Upstream bounded readiness reports.
# Required Context
Authority and dependency results.
# Data Sources
Nexus internal reports.
# Authority Requirements
Internal review only.
# Dependencies
Credit-readiness and business-bankability.
# Allowed Python Executors
None until separately certified.
# Model Routing
GENERAL_REASONING advisory.
# Worker / Profile
NEXUS_FUNDING_WORKER / `nexusworker`.
# Procedure
Check dependencies, identify gaps, formulate review item.
# Output Contract
Recommendation with blockers and confidence.
# Validation
All upstream evidence is present and fresh.
# Side-Effect Validation
Local report only.
# Receipt Requirements
Receipt required.
# Retry Policy
No automatic financial retry.
# Handoff Policy
Ray review worker.
# Failure Modes
Dependency failure or stale evidence.
# Escalation Rules
Fail closed.
# Security Boundaries
No financial authority.
# Examples
Combine two synthetic readiness reports.
