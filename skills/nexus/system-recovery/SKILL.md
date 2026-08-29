---
name: system-recovery
version: 1.0.0
owner: nexus
status: READY_FOR_SYNTHETIC
authority_class: internal_read_only
side_effect_class: local_reports
default_profile: nexusworker
model_policy: LOCAL_PRIVATE
allowed_executors: daily_system_operations
receipt_required: true
---
# Purpose
Classify internal degradation and coordinate safe recovery checks.
# When To Use
When a verified health signal or stale heartbeat requires diagnosis.
# When Not To Use
Never perform destructive repair or service restart without separate authority.
# Inputs
Fresh health evidence and failure signature.
# Required Context
TruthKernel run, dependency, and authority state.
# Data Sources
TruthKernel, runtime reports, and allowlisted diagnostics.
# Authority Requirements
Internal read-only or explicitly bounded recovery authority.
# Dependencies
System operations executor and review worker.
# Allowed Python Executors
`daily_system_operations` for diagnosis only.
# Model Routing
LOCAL_PRIVATE advisory classification.
# Worker / Profile
NEXUS_OPERATIONS_WORKER / `nexusworker`.
# Procedure
Observe, classify, verify dependencies, create follow-up, validate evidence.
# Output Contract
Failure classification and next-action recommendation.
# Validation
No success without fresh evidence.
# Side-Effect Validation
No host mutation in this skill.
# Receipt Requirements
Record failure and recovery fields in loop receipt.
# Retry Policy
At most one evidence-based diagnostic retry.
# Handoff Policy
NEXUS_REVIEW_WORKER for authority decisions.
# Failure Modes
Unavailable service, stale evidence, ambiguous ownership.
# Escalation Rules
Fail closed and preserve degraded state.
# Security Boundaries
No arbitrary restart, shell, or credential use.
# Examples
Classify a synthetic stale heartbeat.
