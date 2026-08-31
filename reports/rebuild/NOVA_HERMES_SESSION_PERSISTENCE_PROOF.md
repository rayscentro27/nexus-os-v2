# Hermes Session Persistence Proof

`SUBPROCESS_LIFETIME=one bounded subprocess per turn`. `HERMES_SESSION_IDENTIFIER=nova-telegram-ab-{chat_id}` and remains stable across turns. The repair explicitly passes the sidecar’s bounded user/assistant history to Hermes’ native `run_conversation(conversation_history=...)` call.

The sidecar persists recent conversational turns and a structured resource-result index. Alpha results now persist request, job, result/receipt, artifact, objective, completion, and status fields. Tool result content is not used as a substitute for provenance.

Development evidence: fresh canonical-worker referent and Alpha sequences completed with runtime/model initialization and zero shadow Telegram sends. The Alpha sequence demonstrated linked IDs; the ordinary comparison sequence still failed to produce a winner because the model delegated too early.
