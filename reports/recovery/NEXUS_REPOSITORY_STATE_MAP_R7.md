# Nexus Repository State Map — R7

Generated 2026-11-17. This is a bounded map; it does not imply Research data has been migrated or that every runtime process has passed protocol/tool-discovery certification.

## Source ownership and checkpoints

| CATEGORY | COUNT | OWNERSHIP | PRESERVED | GIT_PROTECTED | NORMAL_DEVELOPMENT_RISK | NEXT_ACTION |
|---|---:|---|---|---|---|---|
| CANONICAL_SOURCE | 111 verified MCP bridge R3 files; plus subsystem source checkpointed in R5/R7 | Canonical active-source checkpoint is `987c3993f8083c3c44e14728597e404c913cfa0a`; subsystem source has separate scoped commits | YES | YES, in Git | LOW when staging explicit paths | Continue normal development with scoped staging |
| NEW_DEVELOPMENT | 144 baseline source + 104 tests + 35 config/schema candidates; 22 supplemental docs/config/source paths | 17 subsystem commits plus supplemental scoped commits; see commit log | YES | YES, in Git | LOW; no uncheckpointed candidate paths remain | Keep future changes in subsystem commits |
| NOVA_HERMES | Baseline paths included in Nova/Hermes checkpoint; unresolved preservation lineage `efd65d7bb787572d9fde4ede9ef15f53db53849c` | Preserved local source, not certified as the currently deployed Oracle version | YES | YES, in Git | MEDIUM until file-by-file Oracle comparison | Compare later through approved resolver; do not treat as deployed |
| EXPERIMENTAL_SOURCE | 2 baseline candidates plus prior and supplemental experimental lineage | Separate experimental commits; not production-certified | YES | YES, in Git | LOW if kept separate | Keep outside production changes |
| RESEARCH_DATA | 40,404 files in the bounded R6 data/report inventory (overlapping classes; not unique records) | Local source records, findings, provenance, and history; Supabase durability is partial/unknown by collection | YES; originals untouched | NO by design | MEDIUM; preserve and keep out of broad adds | Separate future migration project; no deletion |
| RESEARCH_RUNTIME | Included in local runtime/data inventory; e.g. queue, execution and orchestration state | Local operational state, some active or evolving | YES | NO by design | MEDIUM | Preserve; inspect only with bounded operations |
| RUNTIME_DATABASES | Present under local runtime/data roots; exact total not safely enumerated in this pass | Local state may be active | YES | NO by design | MEDIUM | Keep local; do not copy while active |
| QUEUES | Present in Research runtime datasets; prior R4/R6 inventories include 1,313 queue items | Operational state and provenance may overlap | YES | NO by design | MEDIUM | Preserve; classify before migration or cleanup |
| LOGS | Prior inventory includes 24,287 execution-log records; overlapping data | Runtime history/provenance; not all is durable business knowledge | YES | NO by design | MEDIUM | Keep originals; avoid bulk reads/archives |
| RECEIPTS | Present in Research/runtime evidence collections | Mixed provenance and knowledge | YES | NO by design | MEDIUM | Preserve pending durability mapping |
| REPORTS | R7 bounded dirty inventory includes reports; local historical reports retained | Recovery, certification, research and runtime reporting | YES | Partially tracked; remaining changes classified in `tracked_non_source_r7.txt` | LOW/MEDIUM | Preserve; do not revert without ownership evidence |
| CERTIFICATION | 9 report/certification tracked changes within the 33 remaining tracked non-source edits | Historical evidence | YES | Existing tracked paths preserved | LOW | Keep unless a later explicit retention decision says otherwise |
| GENERATED_FILES | One generated REA notebook is excluded by exact-path ignore; generated CSS remains tracked/modified pending generator proof | Derived output with generator uncertainty for CSS | YES | Exact notebook path ignored; CSS not ignored | LOW/MEDIUM | Validate CSS generator before any revert |
| LOCAL_RUNTIME | 4 supplemental runtime artifacts are exact-path ignored; runtime data remains present | Machine-local worker/service state | YES | Exact paths protected by `.gitignore` | LOW for the four identified paths; other paths require targeted staging | Avoid broad adds |
| LOCAL_CONFIGURATION | 5 tracked local/service configuration modifications remain uncommitted; 9 supplemental LaunchAgent configs were checkpointed | Mix of machine-specific and service configuration | YES | Supplemental definitions versioned; remaining files intentionally unstaged | MEDIUM | Review per deployment/runtime before changing |
| ARCHIVE | Failed incomplete Research archive remains untouched; source originals remain present | Failed recovery artifact, not trusted as backup | YES, but archive is not a valid preservation copy | Not relied on | LOW while originals remain | Do not use as recovery source; no repeat bulk archive |
| UNKNOWN | 0 candidate source/config/test files classified U8; no remaining source candidate from the bounded R7 candidate set | None identified in the scoped candidate pool | YES | N/A | LOW within scope | Keep candidate maps current |

## Candidate disposition

The original R7 candidate map contains exactly 285 entries: 144 `U1_LEGITIMATE_NEW_SOURCE`, 104 `U2_LEGITIMATE_TEST`, 35 `U3_LEGITIMATE_CONFIG_SCHEMA`, and 2 `U4_EXPERIMENTAL_CANARY_SHADOW`; U5–U8 are zero. All 285 are now tracked in scoped commits. The 27 supplemental entries are listed separately: 13 source/docs, 9 configuration files, one generated notebook, and four runtime artifacts. The five generated/runtime entries are protected by exact-path `.gitignore` entries and remain on disk.

Tracked non-source edits went from the R6 baseline of 44 to 33. The remaining 33 are itemized in `tracked_non_source_r7.txt`: 5 local configuration changes, 18 runtime-state/report-runtime files, 9 report/certification files, and one generated CSS file. They are not staged. No source change remains unresolved in the bounded R7 source candidate set.

## Research preservation

Research originals remain intact. No Supabase writes, Research data migration, deletion, bulk archive retry, Oracle mutation, deployment, or service restart occurred. The R6 lightweight manifest is `reports/recovery/research_preservation_manifest_r6.jsonl`. Dataset counts overlap and are not unique-object totals: 32 room records, 31 source records, 547 Alpha finding/receipt records (73 unique finding IDs; 21 direct durable ID matches), 141 NotebookLM/video records, 1,579 orchestration records, 1,313 queue items, 24,287 execution-log records, and 52 shadow cases.

## Active-service spot checks (2026-11-17)

- Launchd reports active PIDs for Research R10 (68016), Research MCP (39334), MCP bridge R3 (582), MCP candidate bridge (571), Research API origin (33046), Cloudflare tunnel (33776), and Google MCP (573).
- Local Research API health and public Cloudflare Research API health returned HTTP 200.
- MCP listeners on 18765 and 18770 returned HTTP 401 without credentials, consistent with authentication being required; authenticated MCP protocol/tool discovery was not tested in this pass.
- `com.nexus.research-mcp-tunnel` and `com.nexus.google-mcp-tunnel` had launchd exit status 255; Research R10 autonomy label showed no current PID. These require separate bounded diagnosis; no restart was attempted.
- The approved Oracle resolver check passed and reported Nova service active and Hermes runtime running. A separate remote command was rejected by the resolver allowlist and was not retried through another connector.

## R7 scoped checkpoints

Subsystem commits: `cda62fea`, `1ef85a4d`, `611ba1ec`, `eecf2cc`, `d8b43825`, `6114dda3`, `af1e3fa9`, `8c147ab1`, `992d837c`, `a04cdfcb`, `1a67972f`, `57bd9b63`, `55f0589f`, `dbc7103f`, `78fedb39`, `835cf941`, `b95b7d81`.

Supplemental commits: `82a18cfe`, `67db4a0e`, `21ed9630`, `69bbec8b`, `d0ba0efe`, `f5df5965`, `3942bb0d`, and exact-path runtime protection `c6c95414`.

Recovery evidence files: `untracked_candidate_map_r7.tsv`, `untracked_candidate_supplement_r7.tsv`, `unresolved_source_r7.txt`, and `tracked_non_source_r7.txt`.
