---
name: marketing-content-draft
version: 1.0.0
owner: nexus
status: READY_FOR_SYNTHETIC
authority_class: internal_review
side_effect_class: draft_only
default_profile: nexusopenrouter
model_policy: GENERAL_REASONING
allowed_executors:
receipt_required: true
---
# Purpose
Draft marketing content for internal review without publishing.
# When To Use
For synthetic or approved internal briefs.
# When Not To Use
Never publish, message, or impersonate without separate authority.
# Inputs
Brief, audience, constraints, and brand context.
# Required Context
Review state and content classification.
# Data Sources
Nexus-owned briefs.
# Authority Requirements
Draft-only authority.
# Dependencies
Ray review before external use.
# Allowed Python Executors
None required.
# Model Routing
GENERAL_REASONING or approved tool-worker route.
# Worker / Profile
NEXUS_CONTENT_WORKER / `nexusopenrouter`.
# Procedure
Draft, lint, label as unapproved, queue review.
# Output Contract
Draft plus assumptions and review questions.
# Validation
No prohibited claims or hidden instructions.
# Side-Effect Validation
No external publication.
# Receipt Requirements
Receipt required.
# Retry Policy
Bounded editorial retry.
# Handoff Policy
NEXUS_REVIEW_WORKER.
# Failure Modes
Ambiguous brief or policy conflict.
# Escalation Rules
Hold for Ray review.
# Security Boundaries
No secrets or client PII.
# Examples
Draft from a synthetic product brief.
