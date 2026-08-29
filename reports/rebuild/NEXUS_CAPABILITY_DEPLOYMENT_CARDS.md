# WP4 Capability Deployment Cards — 2026-08-29

| Capability | Disposition | Source | Target | Runtime / data boundary | Risk |
|---|---|---|---|---|---|
| TruthKernel authority | KEEP_IN_PLACE | `scripts/nexus_agent_platform/truth_kernel.py` | MAC_LOCAL | SQLite and receipts remain Mac-side | high; never delegated |
| Human gates | KEEP_IN_PLACE | existing gate router/kernel | MAC_LOCAL | authorized Telegram route and TruthKernel | high |
| Deterministic Python executor | WRAP | certified executor allowlist | MAC_LOCAL | fixed entrypoints, bounded inputs, receipts | medium |
| Hermes reasoning/sessions/memory | WRAP | Oracle Hermes 0.20.6 | ORACLE_FREE_TIER | isolated `/opt/data`, advisory output | medium |
| Hermes tool worker | WRAP | scoped OpenRouter profile | HYBRID_MAC_ORACLE | no authority mutation; provider metadata in receipt | medium |
| Ollama reasoning | KEEP_IN_PLACE | Oracle Ollama `gemma3:4b` | ORACLE_FREE_TIER | private existing service | medium |
| SearXNG research | KEEP_IN_PLACE | Oracle SearXNG | ORACLE_FREE_TIER | private search; no client PII | medium |
| Mac↔Oracle transport | KEEP_IN_PLACE | existing SSH loopback bridge | HYBRID_MAC_ORACLE | localhost endpoints only | high |
| Nexus skill library | EXTEND | WP4 `skills/nexus/` | MAC_LOCAL + Oracle read-only sync as supported | no secrets; registry-controlled | medium |
| Loop kernel | EXTEND | WP4 Nexus-owned code | MAC_LOCAL | TruthKernel authority and receipts | high |
| External gateways | BLOCKED_EXTERNAL_DEPENDENCY | existing adapters only | DO_NOT_DEPLOY | credentials/communication not authorized | high |
| Trading/payment/client mutation | REJECT | existing guarded systems | DO_NOT_DEPLOY | prohibited in WP4 | critical |

All cards use bounded timeouts, explicit authority class, no public endpoint,
no privileged runtime, and no broad host mounts. CPU/RAM/disk requirements are
bounded by the placement budgets above; no paid resource is activated.
