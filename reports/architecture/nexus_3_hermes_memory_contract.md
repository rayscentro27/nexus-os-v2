# Nexus OS 3.0 — Hermes Memory Contract

Generated: 2026-07-18
Last updated: 2026-07-19 Wave 4A.3 advisory context ownership

## Purpose

Hermes memory supports conversational continuity without becoming policy, approved knowledge, or execution authority.

## Memory types

| Memory type | Scope | Retention | Durable by default | Notes |
|---|---|---:|---|---|
| Immediate prior turn | Current session | Current session | No | Used for simple follow-up continuity |
| Advisory memory | Topic/session | Bounded expiry | No | Holds structured recommendation context: rationale, feasibility, risks, blockers, dependencies, next step, and evidence |
| Active advisory pointer | Conversation session | Current session | No | Points ambiguous follow-ups to the newest recommendation-producing response |
| Advisory history | Conversation session | Bounded last contexts | No | Allows explicit older-topic recall without reactivating stale context |
| Selection memory | Topic/session | Until consumed or topic changes | No | Holds numbered/named recommendation references and most recent selected recommendation |
| Task context | Governed work path | Until completed/cancelled | Existing systems only | Does not execute from chat alone |
| Executive decision memory | Ray-approved decisions | Durable only through approved systems | Yes, when approved | Not created from casual chat |
| Conversation summary memory | Session summary | Bounded | No | Avoids raw permanent transcript storage |
| Page context | Current UI route | Current request | No | Must not override direct conversational meaning |

## Promotion rules

- Memory never becomes approved knowledge automatically.
- Model output never becomes policy automatically.
- Alpha findings never become Hermes facts automatically.
- Casual conversation is not promoted into durable operating memory.
- Executive decision memory requires existing approval/governance paths.

## Topic-change rule

When the user explicitly switches topic, stale advisory and selection context is cleared for canonical conversation handling.

## Advisory ownership rule

Every successful recommendation-producing Hermes response creates a structured advisory context and becomes the active owner for ambiguous follow-ups. The previous active context is marked superseded or inactive and remains available only for explicit older-topic recall.

Recommendation-producing examples:

- Executive priority recommendation.
- Executive risk mitigation.
- Revenue action.
- Project or department recommendation.
- Ranked option list.
- Idea-review conclusion.

Non-replacement examples:

- Greetings.
- Acknowledgements.
- Status answers such as `is Stripe live?`.
- Security-boundary answers such as `can Alpha access Supabase?`.
- Follow-up explanations.
- Conversation-only governed task drafts.

Ambiguous follow-ups resolve in this order:

1. Explicitly named topic or recommendation.
2. Explicit numbered selection.
3. Current active advisory context.
4. Most recent compatible selection context.
5. Most recent compatible task context.
6. Narrow clarification.

P0-P4 priority ranking affects what Hermes recommends, not which prior context owns conversational references.

## Action rule

Memory may resolve a target for an explicit task or Ray Review request, but the result is a conversation-only draft unless the existing governed execution chain persists it.

## Privacy rule

Canonical Wave 4A traces and session state must not store secrets, raw customer documents, credential values, or unnecessary client PII.

## Wave 4A.4 provenance memory

Wave 4A.4 adds bounded previous-answer provenance to the canonical Hermes session.

Stored fields:

- answer ID;
- source type;
- tool IDs;
- evidence IDs;
- source labels;
- evidence state;
- generated timestamp;
- confidence;
- answer kind.

Not stored:

- chain-of-thought;
- raw provider prompts;
- credentials;
- raw client documents;
- unnecessary client PII.

Source-explanation questions such as `where did you get that answer from?` resolve against this bounded provenance record, not a generic advice route.
