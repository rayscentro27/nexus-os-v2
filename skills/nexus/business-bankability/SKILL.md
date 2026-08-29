---
name: business-bankability
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
Evaluate synthetic business-bankability evidence and documentation gaps.
# When To Use
Internal planning with non-production data.
# When Not To Use
Never open accounts, transmit applications, or alter client data.
# Inputs
Synthetic business profile and evidence inventory.
# Required Context
Freshness, source provenance, review authority.
# Data Sources
Nexus fixtures and internal reports.
# Authority Requirements
Internal review only.
# Dependencies
Credit and funding readiness context when present.
# Allowed Python Executors
None until separately certified.
# Model Routing
GENERAL_REASONING advisory.
# Worker / Profile
NEXUS_FUNDING_WORKER / `nexusworker`.
# Procedure
Compare evidence to bounded checklist and report gaps.
# Output Contract
Bankability gap report.
# Validation
No unsupported claims.
# Side-Effect Validation
No external effect.
# Receipt Requirements
Receipt required.
# Retry Policy
One schema correction only.
# Handoff Policy
Ray review.
# Failure Modes
Incomplete or conflicting evidence.
# Escalation Rules
Block when evidence is insufficient.
# Security Boundaries
No client-production mutation.
# Examples
Evaluate a synthetic business packet.
