---
name: python-executor
version: 1.0.0
owner: nexus
status: CERTIFIED_INTERNAL
authority_class: internal_read_only
side_effect_class: allowlisted_local_effect
default_profile: nexusworker
model_policy: LOCAL_PRIVATE
allowed_executors: daily_system_operations
receipt_required: true
---
# Purpose
Select and invoke only certified Nexus Python executors.
# When To Use
When a loop has a matching allowlisted executor.
# When Not To Use
Never accept an arbitrary command, path, or code string from Hermes.
# Inputs
Executor ID and schema-validated context.
# Required Context
Authority, timeout, and side-effect class.
# Data Sources
`NEXUS_PYTHON_EXECUTOR_ALLOWLIST.json`.
# Authority Requirements
Nexus executor broker.
# Dependencies
Fixed Python entrypoint and TruthKernel receipt.
# Allowed Python Executors
Only entries in the canonical allowlist.
# Model Routing
Model is advisory and does not select commands.
# Worker / Profile
NEXUS_OPERATIONS_WORKER / `nexusworker`.
# Procedure
Resolve, validate, run bounded process, validate output, receipt.
# Output Contract
Typed result with artifact hashes.
# Validation
Exit status, artifacts, hashes, and side effects.
# Side-Effect Validation
Expected side effects must match policy.
# Receipt Requirements
Full loop receipt required.
# Retry Policy
Evidence-based bounded retry only.
# Handoff Policy
Review worker on failure.
# Failure Modes
Unknown executor, timeout, nonzero exit, malformed output.
# Escalation Rules
Fail closed.
# Security Boundaries
Arbitrary shell prohibited.
# Examples
Invoke `daily_system_operations`.
