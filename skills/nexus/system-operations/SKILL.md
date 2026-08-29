---
name: system-operations
version: 1.0.0
owner: nexus
status: CERTIFIED_INTERNAL
authority_class: internal_read_only
side_effect_class: local_reports
default_profile: nexusworker
model_policy: LOCAL_PRIVATE
allowed_executors: daily_system_operations
receipt_required: true
---
# Purpose
Run bounded Daily/System Operations diagnostics through the fixed allowlisted executor.
# When To Use
For internal runtime and repository health snapshots.
# When Not To Use
Never for production mutation, payments, trading, or arbitrary shell.
# Inputs
Synthetic or local operational context; no PII.
# Required Context
Freshness, authority, and dependency state from Nexus.
# Data Sources
TruthKernel and `scripts/operations/nexus_daily_monitor.py`.
# Authority Requirements
Internal read-only authority.
# Dependencies
TruthKernel; certified Python executor.
# Allowed Python Executors
`daily_system_operations` only.
# Model Routing
LOCAL_PRIVATE; Hermes review is advisory.
# Worker / Profile
NEXUS_OPERATIONS_WORKER / `nexusworker`.
# Procedure
Resolve skill, run fixed executor, validate artifacts, request advisory review.
# Output Contract
JSON and Markdown diagnostic reports.
# Validation
Required artifacts exist, parse, and hash successfully.
# Side-Effect Validation
Local reports only; no external side effect.
# Receipt Requirements
Use `nexus.loop-receipt.v2`.
# Retry Policy
One bounded retry only after new evidence.
# Handoff Policy
Escalate unresolved failures to `NEXUS_REVIEW_WORKER`.
# Failure Modes
Stale input, executor failure, malformed output, review failure.
# Escalation Rules
Fail closed and create an internal review item.
# Security Boundaries
No arbitrary command, path, credential, or TruthKernel write from Hermes.
# Examples
Run the Daily/System Operations loop with a synthetic status context.
