# Hermes Canonical Reasoning Path Repair

Campaign: `HG-WP6.5-HERMES-CANONICAL-REASONING-PATH-REPAIR-20260830-01`  
Baseline: `7c7bd39`  
Status: development repair complete; fresh real Telegram retest required.

## Root cause

The live WP5 pre-route invokes the deterministic `department_router.execute()` before the optional `try_hermes_platform()` path. `department_router.classify_intent()` returned `UNKNOWN` for semantically valid operating questions that did not contain its narrow phrase patterns. `resolve()` then returned `UNKNOWN_INTENT`, and `execute()` emitted the exact fail-closed response. Because a non-null pre-route response terminates `process_command()`, the platform graph, evidence broker, and Hermes synthesis were never reached.

Nova did not hit this branch. Its separate worker uses Nova semantic mode/capability handling and model-backed planning/context logic, so it produced conversational output instead of the department-router rejection. Nova remains comparison evidence only: its grounding and freshness were not fully proven.

## Repair

For `UNKNOWN` deterministic classifications, the existing Hermes front brain now gets one semantic classification opportunity. Only catalogued read capabilities are mapped to canonical Nexus routes:

- system status → Operations / Daily System Operations
- system health → Operations / System Health Recovery
- pending approvals → Governance / Ray Review
- repository intelligence → System Engineering / Repo Intelligence

The final route still requires canonical registry validation and the existing governed executor. Conversation/advisory results remain non-executing. Unknown or unlisted governed actions remain fail-closed. No phrase-specific synonym list, authority, executor, or registry bypass was added.

## Responsibility split

Hermes performs semantic understanding; the existing LangGraph adapter provides stateful orchestration; Nexus evidence projection and claim validation remain deterministic; TruthKernel remains authoritative for facts, approvals, credentials, eligibility, execution, and receipts. Hermes cannot approve gates, expand capabilities, or claim unsupported actions.

## Before/after evidence status

Before this repair, the Phase A broker and LangGraph path were implemented but not live-used for the five failed messages because routing terminated first. After this repair, the semantic read path can reach canonical route resolution; live use remains unproven until fresh Telegram evidence exists.

## Safety and rollback

Strict administrative commands retain deterministic routing. Existing platform flags and legacy routes remain available for rollback. No new software, provider, credential, service, Active Operator setting, or external action was introduced.
