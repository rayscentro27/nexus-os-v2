# Nexus Active Project Execution Map

Date: 2026-09-27

This is a bounded inventory of meaningful state, not a claim that every record
is advancing. The goal ledger has 24 rows and 12 non-terminal records. The
Research objective projection has 14 projects, all currently
`NEEDS_MORE_RESEARCH`; it is a separate read model.

## Goal-ledger active records

| Project/goal | State | Next action | Classification |
|---|---|---|---|
| `portal.client_beta` | READY_FOR_HUMAN_REVIEW | RAY_REVIEW | WAITING_ON_RAY |
| `portal.admin_control_center` | READY_FOR_HUMAN_REVIEW | RAY_REVIEW | WAITING_ON_RAY |
| `goclear.example_campaign` | READY_FOR_HUMAN_REVIEW | RAY_REVIEW | WAITING_ON_RAY |
| `clyde.entity_readiness` | ACTIVE | CONTINUE_MISSING_CRITERIA | STALLED |
| `customer_service.communications` | ACTIVE | CONTINUE_MISSING_CRITERIA | STALLED |
| `marketing.creative_expansion` | ACTIVE | CONTINUE_MISSING_CRITERIA | STALLED |
| `media.youtube_video` | ACTIVE | CONTINUE_MISSING_CRITERIA | STALLED |
| `distribution.social` | ACTIVE | internal.assemble_final_deliverable | STALLED |
| `finance.capital_management` | ACTIVE | CONTINUE_MISSING_CRITERIA | STALLED |
| `nexus.intent_program_compiler` | ACTIVE | CONTINUE_MISSING_CRITERIA | STALLED |
| `nexus.productization` | PLANNED_DEPENDENCY | none in ledger | NO_NEXT_ACTION |
| `research.continuation_revenue` | ACTIVE | none in ledger | NO_NEXT_ACTION |

## Research-objective projects

The 14 objective projections are `NEEDS_MORE_RESEARCH`. Their follow-up lanes
are represented by the existing Research queue and include CLYDE/FUNDING,
REVENUE/OPPORTUNITY, SYSTEMS, and TRADING. Current follow-up ownership is
primarily `RESEARCH`; this is real ownership for the Research operator, not
proof of department consumption.

## Real advancement canary

| Edge | Evidence | Result |
|---|---|---|
| Handoff → work order | Trading TEST linked to `wo_949ae09e4e6e41ef9d48e662d04c3425` | PASS |
| Work order → owner | `TRADING_ENGINE` | PASS |
| Owner → worker | Existing deterministic Trading intake | PASS |
| Worker → output | `BLOCKED_DEPENDENCY` persisted | PASS |
| Output → review | `TRADING_ENGINE_INTAKE_GATE` | PASS |
| Review → next action | Research ruleset acquisition | PASS |
| Next action → state | `WAITING_DEPENDENCY` | PASS |

The canary is not a successful strategy test. It is a truthful advancement to
a dependency state, with no invented rules and no live trading.

## Bottleneck map

`COMPANY GOAL` PARTIAL → `PROJECT SYSTEM` PARTIAL → `DEPARTMENT` PARTIAL →
`WORKER` FAIL GLOBALLY / PASS SPECIALIZED PATHS → `OUTPUT` PASS WHERE A WORKER
EXISTS → `REVIEW` PASS CANARY / PARTIAL GLOBALLY → `NEXT ACTION` PASS CANARY /
PARTIAL GLOBALLY.

Top systemic defect: no universal handoff-consumer bridge.

Top department defect: most department targets have no claimable consumer.

Top AI workforce defect: registry workers are metadata or empty-executor roles;
only Research AI execution and specialized deterministic Trading consumption
are proven in this scope.

Top project-state defect: goal, Research, and handoff states are not globally
reconciled into one lifecycle transition stream.

## Recovery priorities

1. Connect only departments with a real specialized consumer.
2. Give Systems a bounded isolated benchmark intake before accepting a Systems
   TEST result.
3. Acquire a concrete Trading ruleset through the existing Research return,
   then create a paper/backtest order only after intake passes.
4. Add Revenue, Marketing, Creative, Operations, and Finance consumers only
   when their existing execution contracts are identified.
