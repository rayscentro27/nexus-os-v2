# Repository / Department / Capability Matrix

| Repository or service | Capability | Departments | Execution target | Disposition |
|---|---|---|---|---|
| nexus-os-v2 | TruthKernel, deterministic loops, authority, Python executors | all | MAC_LOCAL | KEEP_IN_PLACE |
| nexuslive | legacy operational patterns | Operations, Governance | MAC_LOCAL | WRAP / reference |
| nexus-ai | agent patterns | Research, Engineering | HYBRID_MAC_ORACLE | MIMIC_PATTERN; no competing scheduler |
| nexus-ai-worker | worker patterns | Operations, Research | ORACLE_FREE_TIER | WRAP only when bounded |
| nexus-hermes-runtime | Hermes source/runtime reference | Research, Engineering | ORACLE_FREE_TIER | KEEP upstream reference |
| nexus-oracle-api | private Oracle integration patterns | Operations, Research | HYBRID_MAC_ORACLE | WRAP |
| nexus-mobile | client interface | Governance | MAC_LOCAL | KEEP interface-only; no authority |
| Oracle Hermes | reasoning, sessions, skills, workers | Operations, Research, Governance | ORACLE_FREE_TIER | KEEP_IN_PLACE |
| Oracle Ollama | private local model inference | Operations, Research | ORACLE_FREE_TIER | KEEP_IN_PLACE |
| Oracle SearXNG | private research retrieval | Research | ORACLE_FREE_TIER | KEEP_IN_PLACE |
| Podman | isolated runtime | Operations, Engineering | ORACLE_FREE_TIER | KEEP_IN_PLACE |

No duplicate scheduler or public endpoint is introduced.
