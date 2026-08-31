# Hermes Referent Root Cause

The isolated Hermes subprocess uses the stable session identifier `nova-telegram-ab-{chat_id}`, but before this campaign `run_conversation()` was called without `conversation_history`. A new subprocess therefore received only the compact sidecar context, not the actual prior user/assistant exchange. The observed failure was compounded when Hermes delegated the initial comparison to Alpha before forming a winner.

Repair: reopen the bounded recent exchange as native Hermes `conversation_history` on every subprocess turn. No phrase-specific resolver or deterministic option mapping was added. A narrow resource description also tells Hermes to reason over a supplied candidate set before optional challenge delegation. The latest rerun preserved the candidates and later referents.
