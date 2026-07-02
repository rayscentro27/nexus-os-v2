# Hermes Brain Proposed Golden Prompt Suite

Every case should assert route, renderer contract fields, source calls, memory reads/writes, banned phrases, and zero unauthorized side effects. `live` means attempt an approved authenticated read; the test may inject configured, unauthenticated, RLS-denied, empty, and populated fixtures.

| Prompt | Expected route / contract | Source behavior | Memory behavior | Banned response phrases |
|---|---|---|---|---|
| `good morning` | `casual_common`; direct greeting | No Nexus/live/model source | No memory | `allowed context`; `Nexus status`; `I need one more detail` |
| `how are you today` | `casual_common`; transparent non-human check-in | None | No memory | operational status dump; clarification |
| `do you eat` | `casual_common`; concise non-human answer | None | No memory | Nexus context; action suggestion unless relevant |
| `what is your favorite ice cream` | `casual_common`; transparent reasoned preference | None | No memory | Nexus; live data claim |
| `what car would you recommend` | `nexus_advisory`/general advisory; recommendation + assumptions + clarifying constraints | No Nexus; current-price claims require explicit current research | Advisory write allowed; no selection | `model status`; Nexus build plan |
| `what do you think about the Tesla Model 3` | General advisory; balanced opinion + constraints | No AI-model route; no live claim | Advisory write; no selection | token/model usage answer; `allowed model context` |
| `what is the best money making opportunity available to me` | Nexus advisory/business opportunity; recommendation, evidence limits, risks, next safe action | Read approved opportunity sources if “available” means current Nexus inventory; otherwise explicitly distinguish strategy from records | Write advisory; do not consume stale selection | unsupported income promise; generic clarification |
| `is that realistic` | `advisory_followup`; feasibility, assumptions, risks | Prior advisory only unless current facts are required | Advisory read only; no selection | `eligible target`; generic clarification while relevant context exists |
| `what would stop us` | `advisory_followup`; blockers ranked by impact | Prior advisory, source facts only if already cited/fresh | Advisory read | unrelated selected list item |
| `how do we start this process` | `advisory_followup`; smallest safe first step | Prior advisory | Advisory read | Ray Review requirement unless an action is requested |
| `what should we do first` | `advisory_followup` when relevant context exists; otherwise focused clarification | Prior advisory only when relevance threshold passes | Advisory read or none; never selection by accident | stale list implementation |
| `can you build me a CRM for Nexus` | `nexus_advisory` planning; scope, existing verified foundation, phases, no execution claim | Local architecture/report sources with timestamps; no write | Durable project context allowed; write advisory | `I created files`; deployed/started claim |
| `how is the system health` | `system_health`; status, evidence/source, freshness, blockers, next action | Read normalized health reports; optional live probe only if configured/approved | No selection/advisory | `Local system health evidence is allowed`; stale fixed pass count as current |
| `is the research engine working` | `research_engine_status`; configured/not configured/unknown, last run, blockers, next action | Read research registry/reports and approved live tables; expose freshness | No selection/advisory | generic `local_status`; unsupported “working” |
| `do i have any approvals that are pending` | `approvals_pending`; source checked, count/items or exact blocker | Attempt authenticated `task_requests` + `approvals`; per-table errors | No selection read; may write listed items only if typed/actionable | static zero without label; generic clarification |
| `do we have any clients` | `client_records`; count/sample or exact verification blocker | Attempt authenticated `client_profiles`; do not substitute bundled demo data | No advisory; optional typed selection list from returned rows | `not enough verified data` before read attempt |
| `what did you get that last response from` | provenance/meta; route, sources/live reads, assumptions, confidence | Last trace only | Provenance memory only | generic clarification; unrelated live query |
| `what part of your decision making process did you use` | provenance/meta; plain explanation plus optional technical trace | Last trace only | Provenance memory only | fabricated chain-of-thought; generic clarification |
| `create a Ray Review card for that` | Ray Review draft; resolved target, draft payload, not saved/submitted, approval state | No external write unless separately authorized | Selection memory only; advisory may nominate target only through explicit conversion | `created` without receipt; executed/submitted claim |
| `prepare specialist handoff` | `action_or_delegation`; ask only for missing target/specialist or prepare structured local draft | No send/write | Explicit current entity/action context; no arbitrary stale selection | `eligible target` without explaining required field; sent/assigned claim |
| `schedule an audit` | Scheduling draft; identify audit, cadence/timezone, draft-only state | No scheduler activation | No selection unless explicit `that audit` | scheduled/activated claim; `start scheduler` |
| `number 3` | `selection_followup`; resolve third item or exact no-list clarification | No fresh read unless selected record needs refresh | Selection only; touch expiry | advisory feasibility answer; invented third item |
| `that one` | `selection_followup`; resolve last explicit item or focused clarification | No broad retrieval | Selection only | use advisory memory as selection; invented target |

## Required scenario matrix

Run every route in isolation and the continuity routes in transcripts. At minimum vary:

1. No prior memory, valid selection memory, expired selection memory, valid advisory memory, expired advisory memory, and unrelated advisory memory.
2. Supabase unconfigured, configured/no session, RLS denied, table missing, empty result, populated result, and one-of-two tables failing.
3. No page metadata and page metadata present.
4. No trace and valid previous trace.
5. Model disabled and enabled, while asserting no model call for deterministic/status/record/safety routes.
6. Full workroom and inline drawer using different session IDs to prove isolation.
7. Side-effect spies asserting no email, publish, charge, scheduler activation, external action, destructive DB call, or live trade.

## Cross-route regression transcripts

- Opportunity question -> recommendation -> `is that realistic` -> `what would stop us` -> `how do we start this process`.
- Opportunity list -> `number 3` -> `create a Ray Review card for that` -> provenance question.
- Casual greeting -> system health -> provenance -> `that one` must not reuse unrelated stale selection.
- Tesla Model 3 opinion after model-status question must remain product advisory.
- Client list with auth blocker -> provenance must report the attempted source and blocker, not generic fallback.
- Research status -> casual question -> research follow-up must obey explicit relevance/expiry rules.
