# Nexus Research → Alpha Intelligence Lineage

## Current truth before repair

The current Phoenix-day window begins at `2026-09-05T07:00:00Z`. The canonical
projection finds:

```text
RESEARCH_NEW_ITEMS=0
ALPHA_EVALUATIONS_SINCE_MIDNIGHT=0
```

This is not the same as the stale activity counter. The persisted activity
artifact `reports/runtime/alpha_research_activity_latest.json` was generated at
`2026-09-05T03:00:26.974673Z` and reported `new_items_discovered=2`. That is
`2026-09-04 20:00:26` in Phoenix, before the requested day. The 09:01Z kernel
cycle did not create those two artifacts; it repeated the internal
`research_c2bbe05fbe2c02d9bd46` candidate in `alpha_outcomes.jsonl`.

For completeness, the two records behind that counter are:

| Item | Source / finding | Research record | Alpha state | Evaluation | Route / status |
|---|---|---|---|---|---|
| The End of Paid Software? 10 Repos You Need to Know | YouTube `o_YngNoGP1I`; source observation persisted as claim `claim_84ce2a0b40dd04b146f7` | `research_56ac934d2ed668056bcb`; content artifact `content_3b6e95bbf8d969257d66` | `CHALLENGED` intake record | None; no canonical score/evaluation record | `growth_experiment_candidate`, downstream `handoff_4f3b781fbb771c160c88`, `CANDIDATE` |
| Watch Me Scale This $13K/Month Coach To $50K (Live Breakdown) | YouTube `N95roD3fcFg`; source observation persisted as claim `claim_4ceb8cea101bd65b57ce` | same Research chain; content artifact `content_512a3164324c23f59fcc` | `CHALLENGED` intake record | None; no canonical score/evaluation record | same Growth evidence handoff, `CANDIDATE` |

The claims are explicitly `source_observation`, `UNVERIFIED`, and marked as
requiring independent verification. The Alpha record is intake/challenge, not
a numerical evaluation. No score or rejection/qualification decision is
present for either item, so the executive answer must say so.

## Root cause

The activity producer in `scripts/alpha/alpha_heartbeat.py` counted newly
persisted content/claims and wrote only aggregate counters to
`alpha_research_activity_latest.json`. The continuous kernel separately
persisted its own Research receipt. Neither path provided the Nova grounding
layer with a joined output → claim → Alpha → routing projection.

The prior `grounded_response.py` branch treated any Research current-state
question as a telemetry request and rendered heartbeat, scheduler, queue, and
counter lines. It therefore surfaced `2 new items` without the records behind
the count. The stale process/telemetry artifacts were also allowed to remain
visible as context even though the current kernel was the authoritative live
executor.

There is no current governed `alpha_evaluations.jsonl` or equivalent scored
record for the two counter-associated items. That is an evidence gap, not a
missing score to infer.

## Intelligence lineage repair

Added `scripts/nexus_agent_platform/research_alpha_lineage.py`, a read-only
projection over the existing governed stores:

- `alpha_content.jsonl`
- `alpha_claims.jsonl`
- `alpha_research.jsonl`
- `alpha_outcomes.jsonl`
- `alpha_discovery_queue.jsonl`
- explicit `alpha_evaluations.jsonl` / `alpha_reviews.jsonl` when present

It joins stable content, claim, Research-chain, evaluation, and downstream
identifiers. It uses the Phoenix local-day boundary for “since midnight,”
preserves provenance, and leaves missing Alpha evaluation fields as absent.
Historical score files without stable lineage are deliberately not joined.

`grounded_response.py` now recognizes the semantic Research-output/Alpha-lineage
query class and selects this projection before the existing Research telemetry
renderer. It renders output names, findings, sources, artifact IDs, verification,
Alpha score/decision/reason when explicitly recorded, routing, current status,
and an explicit unscored/empty result. It does not add a question-specific
handler and does not fabricate activity.

No Alpha pipeline execution was changed: the current evidence shows Alpha intake
and Growth handoff for the two prior-window items, but no scored evaluation to
repair or replay safely.

## Tests

Added `scripts/nexus_agent_platform/tests/test_research_alpha_lineage.py`:

- multiple persisted outputs joined to Alpha evaluations and routes;
- qualified and rejected evaluation records;
- one unscored output;
- temporal filtering;
- explicit empty result with no telemetry substitution;
- natural-language Nova grounding with lineage taking precedence.

Results:

```text
3 passed — test_research_alpha_lineage.py
11 passed — test_wp9z_grounded_response.py
```

The live read-only smoke query returned zero outputs for the current Phoenix
day and two outputs for the counter's actual 03:00Z window, with zero scored
Alpha evaluations in that window.

## Real Telegram certification

Not yet complete. No Telegram message was fabricated. The required remaining
human-origin proof is for Ray to send:

> What did Research produce since midnight, what did Alpha score, and what happened to each item?

The response should be checked for actual persisted lineage and an explicit
zero result, rather than heartbeat telemetry.

## Safety and model separation

This repair is read-only at the executive projection boundary. It changes no
Nova model, prompt, Telegram worker, Research scheduler, Alpha executor, or
external action authority. No customer/outreach/public/financial action was
performed.

## Git

Starting HEAD for this task: `7e837c235bfa54c5bb25f2ea8476801804bc0e4c`.
Task files are limited to the lineage projection, its focused tests, and this
report. Existing unrelated worktree changes remain unstaged.
