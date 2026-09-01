# Session causal ordering repair

Same-chat processing now waits on the existing PID-aware lock rather than
discarding a Telegram update. A dead owner is recoverable; a live owner is
never removed merely because it is old. The poll loop advances the Telegram
offset only after successful processing.

This gives per-session FIFO behavior while leaving different chats/processes
concurrent. No model, Nova profile, Nexus truth, or tool-routing architecture
was changed.
