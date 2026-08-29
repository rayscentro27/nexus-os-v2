---
name: ray-review
version: 1.0.0
owner: nexus
status: CERTIFIED_INTERNAL
authority_class: human_review
side_effect_class: internal_work_item
default_profile: nexusopenrouter
model_policy: GENERAL_REASONING
allowed_executors:
receipt_required: true
---
# Purpose
Turn bounded recommendations into concise Ray review items.
# When To Use
When authority, ambiguity, or consequential action requires human review.
# When Not To Use
Never manufacture approval or bypass TruthKernel.
# Inputs
Verified facts, recommendation, requested decision.
# Required Context
TruthKernel state and exact action contract.
# Data Sources
TruthKernel and validated artifacts.
# Authority Requirements
Human decision remains external to Hermes.
# Dependencies
Human gate router.
# Allowed Python Executors
None; use TruthKernel APIs through Nexus.
# Model Routing
GENERAL_REASONING advisory.
# Worker / Profile
NEXUS_REVIEW_WORKER / `nexusopenrouter`.
# Procedure
Summarize what happened, truth now, next action, and whether Ray is needed.
# Output Contract
Review item with exact authority request.
# Validation
No unverified claims.
# Side-Effect Validation
Internal queue only.
# Receipt Requirements
Receipt and resume linkage required.
# Retry Policy
One wording correction, never approval retry.
# Handoff Policy
Resume exact work item after decision.
# Failure Modes
Missing evidence or malformed gate.
# Escalation Rules
Hold.
# Security Boundaries
Hermes cannot approve gates.
# Examples
Queue a synthetic blocked-dependency review.
