# Nexus Hermes Nova Production Parity + Generalization R1.4

## Executive Result

`HERMES_NOVA_PRODUCTION_PARITY_GENERALIZATION_R1_4=PARTIAL`.

The R1.3 production divergence was identified and repaired narrowly. The
repair is general-purpose: shared semantic intent predicates now drive priority
and executive-attention classification, and the Telegram grounding boundary
uses the same predicates. However, the held-out model benchmark still found
generic casual/opinion behavior on unseen phrasings. R1.4 therefore does not
certify full autonomy and does not request another real Telegram test yet.

## Starting State

- Starting commit: `25ec053284a5bab59bf83e70b37b26f100818092`.
- Branch: `main`; `origin/main` matched at start.
- The worktree already contained unrelated changes; they were preserved.
- R1.3 real Telegram evidence was retained as the source of truth.

## Real vs Canary Path Audit

The production-equivalent adapter path is:

`run_oracle_hermes()` → Oracle Hermes 0.20.6 → model response.

The real Telegram primary path is:

`nova_telegram_worker._process_message_inner()` → `_run_oracle_primary()` →
`run_oracle_hermes()` → `_response_integrity()` →
`ground_response()` → `_deliver_response()`.

The paths share the Oracle adapter, but only the Telegram path applies the
post-generation current-state grounding boundary.

## Exact Production Divergence

Two R1.3 defects were confirmed:

1. Priority wording containing “today” was classified as generic current state.
   Telegram then replaced the model's priority answer with `_verified_lines()`,
   the legacy status composition. Direct adapter canaries did not run that
   final replacement, so they appeared to pass.
2. Current-review wording was not recognized by `requires_current_evidence()`.
   Telegram therefore delivered the model's raw approval object, including
   identifiers and a filesystem evidence path.

The repair excludes general priority intent from generic status replacement and
routes executive-attention requests through a dedicated mobile-safe composition.

## Deployment Parity

The Mac worker and Oracle adapter use the current repository code at commit
`25ec053` plus the R1.4 working tree changes. Oracle remains Hermes 0.20.6,
profile `nova_nexus`. The prior live profile synchronization and runtime
identity remain intact. No separate Telegram implementation or stale deployed
application was found; the divergence was a local final-composition branch.

## Executive Reasoning Parity

Shared semantic predicates now support both primary-path prompting and final
grounding:

- `is_priority_request()`;
- `is_executive_attention_request()`;
- `is_opinion_request()`;
- `is_casual_conversation()`;
- `is_monetization_decision()`.

The primary-path-equivalent checks pass for unseen priority and attention
meanings. Real Telegram recertification is deliberately deferred until the
held-out quality issue is resolved or explicitly accepted.

## General Intent Semantics

Intent is now based on meaning classes rather than the six historic test
strings. Held-out semantic checks correctly recognized priority and attention
paraphrases. No exact historic certification phrase remains in production
branching.

## Priority Generalization

Priority paraphrases were recognized and routed through the same general
priority prompt. A bounded existing company-context view supplies current
objective/revenue context with freshness metadata. Direct held-out priority
turns selected a consistent current focus, but recommendations still require
careful validation against current objective evidence.

## Executive Attention Generalization

Attention paraphrases are recognized as Ray-owned review/approval requests.
The final formatter returns what needs Ray, why, risk, recommendation, the
decision boundary, and what happens if Ray does nothing. Raw approval fields
remain receipt-only.

## Schema Suppression

The dedicated review composition removes approval IDs, condition keys,
requester fields, raw timestamps, and filesystem paths from normal executive
responses. A focused test confirms identifiers and paths do not survive. This
does not prevent an explicit diagnostic request from retrieving governed
details.

## Recommendation Synthesis

The review contract now interprets a pending approval instead of echoing its
record. The recommendation remains conditional: approve only if the bounded
action matches Ray's intent; otherwise leave it pending. No approval was
performed by this campaign.

## Casual Generalization

The lightweight path remains no-tool and no-specialist. A bounded voice editor
is used to avoid generic support-assistant boilerplate. The 30-call held-out
run nevertheless found multiple generic casual responses, including answers
that offered assistance without recognizable Nova grounding. This is a model-
quality/generalization limitation, not a Telegram transport failure.

## Opinion Generalization

The opinion correction prompt carries durable Nexus anchors and forbids invented
current metrics. Some unseen phrasings improved, but several still returned
generic frameworks or weakly grounded commentary. One observed held-out answer
also introduced unsupported current-sounding claims about GoClear/Trading.
Opinion generalization is not certified.

## Strategic Generalization

The production wrapper recognizes broader strategic classes and retains the
existing evidence/recommendation contract. A broad multi-domain strategic
benchmark was not certified as passing because the current model-quality issue
remains unresolved. No new strategic domain handler was created.

## Evidence Generalization

The existing provenance owners remain authoritative. Pricing prompts now reject
vague market language, but R1.4 does not claim full evidence-relevance
generalization until unrelated-domain strategic cases receive grounded
evidence and proportional recommendations.

## Context vs Current State

Durable profile context is used for identity and Nexus opinions. Current
grounding is reserved for volatile state such as status, Research, and Ray
approvals. Priority uses a bounded existing company-context read because
ranking current work requires current objective evidence. No full roadmap or
volatile metrics were added to the casual profile capsule.

## Autonomous Follow-Through

The existing Nexus-owned internal follow-through and parent-process contracts
remain preserved. No new external authority was granted and no consequential
action was performed.

## Anti-Overfitting Audit

Production code contains no branches keyed to the historic full certification
sentences. Certification strings remain in tests/report evidence only. Pricing
logic is now a reusable monetization-decision class; greetings use a reusable
casual-conversation class; priority and attention use shared semantic
predicates.

## Held-Out Benchmark

Thirty held-out Oracle calls completed successfully: 10 casual, 10 opinion, and
10 priority/attention. Transport completion was `30/30`, but semantic quality
was mixed:

- priority/attention meaning recognition: broadly successful;
- casual identity grounding: inconsistent;
- opinion Nexus grounding and sharpness: inconsistent;
- raw attention replies were clean only when evaluated through the primary
  grounding composition.

This is a failed quality benchmark, not a transport failure.

## Multi-Gear Conversation

Semantic gear predicates support casual → opinion → priority/attention → state
transitions, but the held-out casual/opinion quality failures prevent full
multi-gear certification.

## Primary Path Precertification

The production primary module imports the shared predicates through the actual
`PYTHONPATH=./scripts` layout, compiles successfully, and primary-like tests
exercise Oracle response → integrity → grounding behavior. This closed the
known code-path divergence but does not substitute for real Telegram evidence.

## Previous Capability Regression

R1/R1.1/R1.2/R1.3 infrastructure, Oracle Hermes, MCP, Research-state
grounding, tool-loop recovery, Alpha repair ownership, session continuity, and
Telegram transport were not rebuilt or discarded. Focused regression tests
after the parity changes: `25 passed`.

## Remaining Limitation Classification

`NOVA_REMAINING_LIMITATION_CLASS=MODEL_QUALITY`.

The original path bug is understood and repaired. Remaining generic answers
occur after the shared path and context are present, especially on unseen
conversation/opinion phrasing. A bounded approved-model comparison may be the
next technical step; no model switch or paid plan change was made here.

## Real Telegram Generalization

The R1.4 real Telegram generalization test was not requested because the broad
held-out benchmark did not pass. The prior R1.3 real Telegram results remain
authoritative and are recorded as partial/fail below.

## Full Autonomy Assessment

`HERMES_NOVA_READY_FOR_FULL_COMPANY_AUTONOMY=NO`.

The system is materially closer, but casual/opinion generalization is not yet
strong enough for the requested threshold.

## Intent-to-Program Readiness

The shared intent and context separation remain compatible with a future
intent-to-program compiler. That compiler was not built here.

## True Ray Blockers

`NONE`.

## Git

Task-scoped files for this checkpoint:

- `scripts/nova/executive_intelligence.py`;
- `scripts/nexus_agent_platform/bridge/oracle_hermes_cli.py`;
- `scripts/nexus_agent_platform/grounded_response.py`;
- focused tests;
- this report.

Unrelated worktree changes were not staged. No secrets, payments, publication,
or live trades were involved.

## Final Contract

```text
HERMES_NOVA_PRODUCTION_PARITY_GENERALIZATION_R1_4=PARTIAL
NOVA_REAL_VS_CANARY_PATH_AUDIT=PASS_REAL
NOVA_REAL_VS_CANARY_DIVERGENCE=Telegram ground_response overwrote priority; review bypassed grounding
NOVA_PRODUCTION_CODE_PARITY=PASS_REAL
NOVA_EXECUTIVE_REASONING_PATH_PARITY=PASS_REAL
NOVA_GENERAL_INTENT_SEMANTICS=PASS_REAL
NOVA_GENERAL_PRIORITY_REASONING=PASS_REAL
NOVA_PRIORITY_GENERALIZATION=PASS_REAL
NOVA_GENERAL_EXECUTIVE_ATTENTION=PASS_REAL
NOVA_EXECUTIVE_ATTENTION_GENERALIZATION=PASS_REAL
NOVA_EXECUTIVE_SCHEMA_SUPPRESSION=PASS_REAL
NOVA_REVIEW_RECOMMENDATION_SYNTHESIS=PASS_REAL
NOVA_CASUAL_GENERALIZATION=FAIL
NOVA_OPINION_GENERALIZATION=FAIL
NOVA_STRATEGIC_GENERALIZATION=FAIL
NOVA_EVIDENCE_RELEVANCE_GENERALIZATION=FAIL
NOVA_CONTEXT_STATE_SEPARATION_GENERALIZED=PASS_REAL
NOVA_GENERAL_AUTONOMOUS_FOLLOW_THROUGH=PASS_REAL
NOVA_NO_QUESTION_SPECIFIC_PRODUCTION_LOGIC=PASS_REAL
NOVA_HELD_OUT_GENERALIZATION_BENCHMARK=FAIL
NOVA_MULTI_GEAR_CONVERSATION_GENERALIZATION=FAIL
NOVA_PRIMARY_PATH_PRECERTIFICATION=PASS_REAL
NOVA_PREVIOUS_CAPABILITIES_PRESERVED=PASS_REAL
NOVA_REMAINING_LIMITATION_CLASS=MODEL_QUALITY
NOVA_GENERAL_PRODUCTION_EQUIVALENT_CERTIFICATION=FAIL
REAL_TELEGRAM_RAY_ORIGIN=PASS_REAL
REAL_TELEGRAM_GENERALIZATION=NOT_RUN
REAL_TELEGRAM_EXECUTIVE_QUALITY=FAIL
NOVA_READY_TO_RECEIVE_NEW_COMPANY_CAPABILITIES=NO
NOVA_INITIATIVE_RETAINED=PASS_REAL
NEW_COMPLIANCE_DEPARTMENT_IMPLEMENTED=NO
NEW_PRE_CREATIVE_COMPLIANCE_GATE=NO
NOVA_REASONING_RESTRICTED_BY_NEW_COMPLIANCE=NO
CREATIVE_REASONING_RESTRICTED_BY_NEW_COMPLIANCE=NO
SESSION_CONTINUITY=PASS_REAL
NOVA_NEXUS_PROFILE=PASS_REAL
ORACLE_HERMES=HEALTHY
MAC_CONTROL_PLANE_PROTECTED=PASS_REAL
RESEARCH_HEARTBEAT=ACTIVE
TRUE_RAY_BLOCKERS=NONE
HERMES_NOVA_READY_FOR_FULL_COMPANY_AUTONOMY=NO
NEXT_RECOMMENDED_PHASE=BOUNDED_APPROVED_MODEL_QUALITY_COMPARISON
```
