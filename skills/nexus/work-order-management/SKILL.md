---
name: work-order-management
version: 1.0.0
owner: nexus
status: CERTIFIED_BOUNDED
authority_class: internal_execution
side_effect_class: internal_task_state
default_profile: nexusopenrouter
model_policy: TOOL_CAPABLE
allowed_executors:
receipt_required: true
---
# Purpose
Coordinate governed work orders and Hermes worker handoffs.
# When To Use
For bounded internal tasks with explicit worker and executor allowlists.
# When Not To Use
Never grant arbitrary shell or consequential authority.
# Inputs
Work order, skill, worker, profile, model, and executor policy.
# Required Context
TruthKernel authority and dependencies.
# Data Sources
Nexus work orders and Hermes Kanban state.
# Authority Requirements
Internal execution only.
# Dependencies
Certified Hermes tool-worker route.
# Allowed Python Executors
Only resolver-approved executors.
# Model Routing
TOOL_CAPABLE for lifecycle tools.
# Worker / Profile
NEXUS_OPERATIONS_WORKER or NEXUS_REVIEW_WORKER.
# Procedure
Create, assign, execute, handoff, review, complete, receipt.
# Output Contract
Correlated task and loop receipt.
# Validation
Task state transitions are explicit.
# Side-Effect Validation
Internal state only.
# Receipt Requirements
Task ID and receipt ID required.
# Retry Policy
Three distinct corrections maximum per signature.
# Handoff Policy
Only declared handoff targets.
# Failure Modes
Unavailable worker, malformed result, stale task.
# Escalation Rules
Fail closed.
# Security Boundaries
No TruthKernel mutation by Hermes.
# Examples
Run a synthetic worker handoff.
