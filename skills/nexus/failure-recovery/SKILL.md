---
name: failure-recovery
version: 1.0.0
owner: nexus
status: READY_FOR_SYNTHETIC
authority_class: internal_read_only
side_effect_class: local_receipts
default_profile: nexusworker
model_policy: LOCAL_PRIVATE
allowed_executors:
receipt_required: true
---
# Purpose
Apply bounded evidence-based retry, handoff, and recovery classification.
# When To Use
After a loop or worker failure with a known signature.
# When Not To Use
Never repeat identical failures indefinitely or invent success.
# Inputs
Failure receipt, signature, retry count, and recovery policy.
# Required Context
TruthKernel state and authority boundary.
# Data Sources
Loop receipts and verified artifacts.
# Authority Requirements
Only policy-approved internal recovery.
# Dependencies
Loop kernel and review worker.
# Allowed Python Executors
Resolver-approved executor only.
# Model Routing
LOCAL_PRIVATE advisory diagnosis.
# Worker / Profile
NEXUS_REVIEW_WORKER / `nexusworker`.
# Procedure
Classify, choose distinct correction, retry or handoff, verify, receipt.
# Output Contract
Recovery decision with evidence.
# Validation
No verified state without fresh output.
# Side-Effect Validation
External effects remain false unless separately authorized.
# Receipt Requirements
Link original and recovery receipts.
# Retry Policy
Maximum three materially distinct attempts.
# Handoff Policy
Declared worker targets only.
# Failure Modes
Repeated signature, unavailable dependency, malformed result.
# Escalation Rules
Mark blocked after limit.
# Security Boundaries
No authority expansion.
# Examples
Fail closed on a malformed executor result.
