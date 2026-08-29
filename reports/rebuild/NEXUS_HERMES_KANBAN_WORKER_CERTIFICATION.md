# Hermes Kanban / Worker Certification — 2026-08-29

Native Kanban initialized `/opt/data/kanban.db`, exposed durable SQLite task
storage, profile assignment, isolated scratch workspaces, dispatcher claims,
run history, reclaim, block, and archive operations.

| Criterion | Result | Evidence |
|---|---|---|
| KANBAN_NATIVE | YES | tagged CLI help and initialized DB |
| KANBAN_TASK_CREATE_ASSIGN_DISPATCH | PASS | three real tasks dispatched |
| MULTI_PROFILE_ISOLATION | PASS | default and `nexuscert` profiles exist separately |
| WORKER_MODEL_EXECUTION | BLOCKED | Ollama gemma3:4b rejects injected Kanban tools; Groq route returned 403 |
| TASK_LIFECYCLE / HANDOFF / RESTART_RESUME | NOT_PROVEN | blocked before worker protocol completion |

The failed tasks were campaign-created synthetic tasks and were archived to
stop automatic retry. No external side effect occurred. Nexus TruthKernel
remains the authoritative work-order record; Hermes Kanban is coordination
only.
