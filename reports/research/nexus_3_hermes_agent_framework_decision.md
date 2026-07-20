# Nexus 3 Hermes Agent Framework Decision

Generated: 2026-07-20

## SELECTED_APPROACH

NEXUS_NATIVE_SUFFICIENT for Wave 4A.4.

## Reason

The observed Hermes defects were not caused by a missing agent framework. They were caused by narrow canonical response coverage after mode classification: broad factual, report, customer, provenance, topic-continuation, and design questions reached a generic default response instead of governed evidence tools.

## Framework Evaluation

| Candidate | Useful capability | Nexus overlap | License / hosting / PII risk | Runtime cost | Disposition |
|---|---|---|---|---|---|
| LangGraph | Durable graph state, checkpoint patterns, bounded node transitions | Nexus already has deterministic router, Capability OS, traces, and approval gates | OSS dependency; safe if self-hosted, but adds graph runtime complexity | Medium | STUDY_PATTERN_ONLY |
| Mem0 | Long-term memory extraction and retrieval | Nexus memory is intentionally bounded and not auto-promoted into knowledge | External memory hosting can create PII exposure unless self-hosted/reviewed | Medium | DEFER |
| Zep | Conversation memory service and retrieval | Nexus needs provenance and policy-bound memory, not a hosted memory layer yet | Hosted memory introduces customer/privacy governance work | Medium | DEFER |
| Letta | Agent memory/state concepts | Nexus already separates brain profiles, memory, evidence, and policy | Heavy agent abstraction; state persistence requires security review | High | STUDY_PATTERN_ONLY |
| Nexus-native tool orchestration | Deterministic policy, read-only tool registry, provenance, certification | Directly matches Capability OS and existing Hermes architecture | No new external data hosting or PII movement | Low | NEXUS_NATIVE_SUFFICIENT |

## Measured Gap

Generic fallback root cause: `src/lib/hermes/hermesResponseStrategy.ts` returned the same response for `EXPLANATION`, `FACTUAL_QUESTION`, `IDEA_REVIEW`, and `DECISION_SUPPORT` when no executive intent matched.

## Expected Benefit

The selected approach fixes the live defects with:

- governed Hermes Tool Registry;
- read-only current-time, project-status, report, customer aggregate, and provenance tools;
- project discussion mode;
- active-topic planning continuation;
- 200+ corpus and 40+ holdout tests.

## Risks

- Live provider state remains evidence-conflicted until a focused authenticated provider smoke test verifies the deployed `hermes-chat` route.
- Report catalog uses the sanitized bundled registry, not arbitrary filesystem scans.
- Customer answers remain aggregate/read-model only and do not prove active paying customers.

## Rollback

Revert Wave 4A.4 changes to `src/lib/hermes/hermesGeneralTools.ts`, `hermesModeClassifier.ts`, `hermesResponseStrategy.ts`, `hermesConversationEngine.ts`, `hermesMemoryResolver.ts`, and the capability registrations. The older deterministic Workroom path remains available.

## Current Installation State

No external framework was installed.
