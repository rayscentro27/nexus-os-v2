# WP4 Worker / Skill / Model / Executor Routing — 2026-08-29

Routing is deny-by-default and resolves four distinct identities:

`skill_id → worker_id → profile/model policy → executor_id`.

The canonical worker map is `data/runtime/nexus_worker_role_map.json`; skill
metadata is `data/runtime/nexus_skill_registry.json`; route enforcement is
`scripts/nexus_agent_platform/loops/routing.py`.

| Worker | Primary skills | Model policy | Executor boundary |
|---|---|---|---|
| NEXUS_OPERATIONS_WORKER | system operations/recovery, Python executor | LOCAL_PRIVATE; TOOL_CAPABLE for lifecycle tools | daily_system_operations |
| NEXUS_RESEARCH_WORKER | research, repository intelligence | RESEARCH / CODE_ASSIST | none until certified |
| NEXUS_REVIEW_WORKER | Ray review, recovery, work orders | GENERAL_REASONING / TOOL_CAPABLE | none; review only |
| NEXUS_CLIENT_LIFECYCLE_WORKER | client lifecycle, Ray review | GENERAL_REASONING | none; authority blocked |
| NEXUS_FUNDING_WORKER | credit, bankability, funding | GENERAL_REASONING | none; synthetic only |
| NEXUS_CONTENT_WORKER | marketing draft, Ray review | GENERAL_REASONING | none; draft only |

Unknown skill, mismatched worker, unauthorized model policy, and executor
mismatch fail closed. No route grants arbitrary shell, TruthKernel writes,
payments, live trading, client mutation, or external outreach.
