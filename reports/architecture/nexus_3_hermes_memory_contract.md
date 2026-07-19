# Nexus OS 3.0 — Hermes Memory Contract

Generated: 2026-07-18

## Purpose

Hermes memory supports conversational continuity without becoming policy, approved knowledge, or execution authority.

## Memory types

| Memory type | Scope | Retention | Durable by default | Notes |
|---|---|---:|---|---|
| Immediate prior turn | Current session | Current session | No | Used for simple follow-up continuity |
| Advisory memory | Topic/session | Bounded expiry | No | Holds recommendations and rationale |
| Selection memory | Topic/session | Until consumed or topic changes | No | Holds numbered/named recommendation references |
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

## Action rule

Memory may resolve a target for an explicit task or Ray Review request, but the result is a conversation-only draft unless the existing governed execution chain persists it.

## Privacy rule

Canonical Wave 4A traces and session state must not store secrets, raw customer documents, credential values, or unnecessary client PII.
