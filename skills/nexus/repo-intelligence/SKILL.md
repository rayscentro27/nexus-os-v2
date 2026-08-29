---
name: repo-intelligence
version: 1.0.0
owner: nexus
status: READY_FOR_SYNTHETIC
authority_class: internal_read_only
side_effect_class: local_reports
default_profile: nexusworker
model_policy: CODE_ASSIST
allowed_executors:
receipt_required: true
---
# Purpose
Inspect repository state and produce bounded engineering recommendations.
# When To Use
For static repository and test-state analysis.
# When Not To Use
Never self-modify production code or push unreviewed changes.
# Inputs
Repository path from a Nexus allowlist and requested question.
# Required Context
Commit, working-tree, and authority state.
# Data Sources
Nexus repository and reports.
# Authority Requirements
Read-only inspection.
# Dependencies
Codex remains the engineering actor.
# Allowed Python Executors
No arbitrary executor; static inspection only.
# Model Routing
CODE_ASSIST advisory route.
# Worker / Profile
NEXUS_RESEARCH_WORKER / `nexusworker`.
# Procedure
Inspect, compare, classify, recommend, create internal work item.
# Output Contract
Evidence-backed recommendation.
# Validation
Paths and commit are recorded.
# Side-Effect Validation
No code mutation.
# Receipt Requirements
Receipt includes repository commit and artifact hash.
# Retry Policy
One bounded re-read after changed evidence.
# Handoff Policy
NEXUS_REVIEW_WORKER.
# Failure Modes
Dirty tree, missing path, test uncertainty.
# Escalation Rules
Never infer operational health from source presence.
# Security Boundaries
No shell injection or secret inspection.
# Examples
Classify duplicate loop implementations.
