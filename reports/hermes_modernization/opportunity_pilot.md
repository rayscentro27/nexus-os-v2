# Opportunity Pilot

## Pilot scope

This pilot used public or governed internal evidence only.

It did not:

- touch client PII
- publish anything publicly
- spend money
- send autonomous outreach
- deploy production changes

## Pilot flow

1. Collect governed opportunity and research inputs.
2. Normalize records into a canonical opportunity shape.
3. Deduplicate identical records.
4. Score deterministically in Python.
5. Compare against prior structured state.
6. Use AI only when the signal is materially new or high value.
7. Merge AI interpretation without overwriting deterministic score fields.
8. Produce a canonical opportunity record and a business-case skeleton.

## Example result

The current benchmark path produced a canonical record with:

- `id`: `opp_2`
- `base_score`: `74`
- `opportunity_score`: `74`
- `status`: `DISCOVERED`
- `business_case.revenue_potential`: `1500`
- `business_case.recommended_next_action`: `Collect more evidence and validate demand.`

## Pilot outcome

- Canonical record writing works.
- Deterministic scoring is stable.
- AI interpretation is compact and bounded.
- Duplicate opportunities are collapsed.
- The opportunity engine remains read-only and does not create a new store.

## Stop condition

The pilot stops at the business-case skeleton stage.
No build, launch, outreach, or public publishing was attempted.
