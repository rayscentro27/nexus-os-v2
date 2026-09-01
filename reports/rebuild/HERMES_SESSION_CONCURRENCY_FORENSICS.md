# Session concurrency forensics

The worker used an atomic per-chat lock, but `_process_message_inner` treated a
busy lock as “Skipped update” and `run_poll` advanced `max_update_id` regardless
of `process_message` success. This is a turn-loss path, not safe ordering.

The live records available for this audit show sequential completion, so they do
not prove an actual overlap in that particular morning run. The code path proves
that a second worker could be dropped during an in-flight Hermes turn. The
repair waits for a live owner to release the lock and recovers only dead-owner
locks.
