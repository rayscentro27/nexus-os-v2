---
name: model-routing
version: 1.0.0
owner: nexus
status: CERTIFIED_BOUNDED
authority_class: advisory
side_effect_class: none
default_profile: nexusopenrouter
model_policy: LOCAL_PRIVATE,TOOL_CAPABLE,FALLBACK
allowed_executors:
receipt_required: true
---
# Purpose
Choose a verified provider/model policy for a bounded loop.
# When To Use
At loop planning and review boundaries.
# When Not To Use
Never silently activate paid or unverified providers.
# Inputs
Task class, data classification, provider inventory.
# Required Context
Cost and credential policy.
# Data Sources
Nexus provider matrix and Hermes route metadata.
# Authority Requirements
Nexus policy controls selection.
# Dependencies
Oracle Ollama and scoped OpenRouter route.
# Allowed Python Executors
None.
# Model Routing
LOCAL_PRIVATE first for private reasoning; TOOL_CAPABLE only for tool workers.
# Worker / Profile
Worker-specific profile selected by resolver.
# Procedure
Classify, select certified route, record metadata, fail closed if none.
# Output Contract
Provider, model, policy, and fallback disposition.
# Validation
Route is present, authorized, and compatible.
# Side-Effect Validation
No side effect.
# Receipt Requirements
Record provider/model in receipt.
# Retry Policy
Only declared fallback routes.
# Handoff Policy
Review on provider failure.
# Failure Modes
403, 429, incompatible tools, cost block.
# Escalation Rules
BLOCKED_EXTERNAL_DEPENDENCY.
# Security Boundaries
No secret values in context.
# Examples
Select Ollama for private status reasoning.
