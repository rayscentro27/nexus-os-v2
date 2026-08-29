---
name: client-lifecycle
version: 1.0.0
owner: nexus
status: BLOCKED_AUTHORITY
authority_class: human_authority_required
side_effect_class: client_production_mutation
default_profile: nexusworker
model_policy: GENERAL_REASONING
allowed_executors:
receipt_required: true
---
# Purpose
Prepare governed client-lifecycle recommendations without production mutation.
# When To Use
Only synthetic fixtures or explicitly approved review preparation.
# When Not To Use
Never change client records or contact clients automatically.
# Inputs
Synthetic lifecycle state.
# Required Context
Human authority and data classification.
# Data Sources
Nexus client lifecycle models, read-only.
# Authority Requirements
Separate human authority for any mutation.
# Dependencies
TruthKernel gate and review.
# Allowed Python Executors
None in this campaign.
# Model Routing
GENERAL_REASONING advisory.
# Worker / Profile
NEXUS_CLIENT_LIFECYCLE_WORKER / `nexusworker`.
# Procedure
Classify state and create review work item.
# Output Contract
Advisory lifecycle recommendation.
# Validation
No mutation occurred.
# Side-Effect Validation
Must be zero external effects.
# Receipt Requirements
Receipt required.
# Retry Policy
No autonomous retry for client actions.
# Handoff Policy
Ray review.
# Failure Modes
Missing authority, stale client state.
# Escalation Rules
Block and request exact gate.
# Security Boundaries
PII denied to external models.
# Examples
Classify a synthetic onboarding state.
