# WP8.3.5 Local Trading Repository Inventory

Audit date: 2026-09-01. No standalone Vibe-Trading git repository, CLI, Python
module, or package metadata was found. `~/.vibe-trading` is a memory directory
only.

Relevant local repositories:

| Repository | Remote / HEAD | Relevant material | Decision |
|---|---|---|---|
| `~/nexus-ai` | `rayscentro27/nexuslive.git`, `ec879d2` | trading-engine, strategy agent, risk, broker, backtest | REFERENCE_ONLY / ADAPT |
| `~/nexuslive` | `rayscentro27/nexuslive.git`, `4fb57df` | trading-engine, strategy lab | REFERENCE_ONLY / ADAPT |
| `~/nexuslive/nexus-strategy-lab` | nested legacy project | ingestion, scoring, Hermes review, backtest, paper journal, metrics | ADAPT |
| `~/nexus-hermes-runtime` | `NousResearch/hermes-agent`, `3c27eb623` | Hermes runtime/native workers, skills, tools, sessions | PRESERVE / REFERENCE |
| `~/nexus-claw3d` | `iamlukethedev/Claw3D`, `06e2cbd` | agent/orchestration concepts | CONCEPT_ONLY |

No Freqtrade, VectorBT, Backtrader, FinRL, or additional Lean checkout was
found in the bounded local search. No repository was modified.

