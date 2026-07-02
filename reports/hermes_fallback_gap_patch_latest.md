# Hermes Fallback Gap Patch

Generated: 2026-07-01 18:48 America/Phoenix

The selection-specific target prompt is no longer the global fallback. It is restricted to vague action references such as “Delegate this” when no eligible target exists.

General unknown questions receive a softer routing choice. Verified-record questions without data receive an explicit record-context response. Trace questions without history receive the existing no-trace response. Greetings, common knowledge, advice, activity summaries, and source-reason questions do not use an unresolved-selection fallback.

No action is executed by these paths. Approval gates remain intact.
