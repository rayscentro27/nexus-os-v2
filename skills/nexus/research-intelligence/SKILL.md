---
name: research-intelligence
version: 1.0.0
owner: nexus
status: READY_FOR_SYNTHETIC
authority_class: read_only
side_effect_class: local_reports
default_profile: nexusopenrouter
model_policy: RESEARCH
allowed_executors:
receipt_required: true
---
# Purpose
Produce source-validated research recommendations using approved private research paths.
# When To Use
For public, bounded research objectives.
# When Not To Use
Never send client PII or execute financial actions.
# Inputs
Research question, scope, freshness, and source constraints.
# Required Context
Authority and data classification.
# Data Sources
Nexus/SearXNG research adapters.
# Authority Requirements
Read-only research authority.
# Dependencies
Private SearXNG and source validation.
# Allowed Python Executors
Only a separately certified research executor; none is implied here.
# Model Routing
RESEARCH through approved scoped provider.
# Worker / Profile
NEXUS_RESEARCH_WORKER / `nexusopenrouter`.
# Procedure
Gather sources, validate provenance, summarize, and receipt findings.
# Output Contract
Evidence-linked recommendation with uncertainty.
# Validation
Source URLs and timestamps are present and consistent.
# Side-Effect Validation
No external mutation.
# Receipt Requirements
Record sources, model metadata, and hashes.
# Retry Policy
Bounded source retry; no invented sources.
# Handoff Policy
Review worker for ambiguity.
# Failure Modes
No sources, stale data, provider unavailable.
# Escalation Rules
Mark blocked or insufficient evidence.
# Security Boundaries
PII denied by default.
# Examples
Research a synthetic public market topic.
