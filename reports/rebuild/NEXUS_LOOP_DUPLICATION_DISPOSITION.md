# Nexus Loop Duplication Disposition — 2026-08-29

| Existing area | Disposition | Reason |
|---|---|---|
| WP3 Daily/System Operations | MIGRATE / WRAP | Reuse fixed executor; v2 kernel owns orchestration |
| TruthKernel and human gates | KEEP | Authority and verified truth remain Mac-side |
| Python executor broker | WRAP | Existing allowlist is the execution boundary |
| Hermes sessions, memory, profiles | WRAP | Native state remains Oracle-local; Nexus records receipts |
| Hermes Kanban/workers | WRAP | Hermes coordinates bounded workers; Nexus work orders remain authority |
| Older `nexuslive` and `nexus-ai` implementations | MIMIC_PATTERN | Preserve rollback/reference; do not run competing schedulers |
| Existing SearXNG/Ollama services | KEEP_IN_PLACE | Healthy Oracle services; no duplicate deployment |
| Old loop registry | KEEP_AS_HISTORICAL | v2 registry is descriptive canonical WP4 registry |

No old implementation was deleted. Duplicate runtime identities are resolved
by explicit placement and primary/fallback documentation.
