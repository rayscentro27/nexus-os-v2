# Hermes Kanban / Worker Certification — 2026-08-29

Native Kanban initialized `/opt/data/kanban.db`, exposed durable SQLite task
storage, profile assignment, isolated scratch workspaces, dispatcher claims,
run history, reclaim, block, and archive operations.

| Criterion | Result | Evidence |
|---|---|---|
| KANBAN_NATIVE | YES | tagged CLI help and initialized DB |
| KANBAN_TASK_CREATE_ASSIGN_DISPATCH | PASS | three real tasks dispatched |
| MULTI_PROFILE_ISOLATION | PASS | default and `nexuscert` profiles exist separately |
| WORKER_MODEL_EXECUTION | PASS_WITH_SCOPED_PROVIDER | OpenRouter `minimax/minimax-m2.7:free` accepted lifecycle tools and completed a bounded worker canary; Ollama remains reasoning-only |
| TASK_LIFECYCLE / HANDOFF | PASS | create → claim → lifecycle tool use → comment → review request → governed completion |
| WORKER_STATE_PERSISTENCE / RESTART_RESUME | PASS | completed task remained `done` after Hermes container restart; API returned healthy |

Earlier failed tasks were campaign-created synthetic tasks and were archived to
stop automatic retry. The successful canary was synthetic and caused no
external side effect. Nexus TruthKernel remains the authoritative work-order
record; Hermes Kanban is coordination only.
