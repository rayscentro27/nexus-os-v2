# Nexus Ray Review Queue

Ray Review Queue is a focused decision room. It is not a research backlog.

## What Goes In

- campaigns ready to publish
- emails, social posts, SMS, DMs, or client/lead contact ready to send
- ads or spend decisions
- scheduler activation
- production changes
- connector setup requiring Ray's decision
- revenue opportunities where Hermes recommends Ray choose direction
- compliance-sensitive actions
- trading items that suggest anything beyond paper-only research
- high-value strategic choices and report reviews

## What Does Not Go In

- transcript review
- video scoring
- SEO keyword scoring
- affiliate page scoring
- watched resource updates
- department routing
- internal experiment cards
- internal reports
- paper-only trading research cards
- Hermes internal recommendations

## Difference From Approvals

Approvals are the execution gate. Ray Review Queue is the decision layer before execution. A review item can result in "prepare", "request changes", "park", or "create formal approval item", but it does not execute anything by itself.

## Difference From Internal Review

Internal review means Nexus or Hermes should look closer. Ray Review Queue means Ray has a real decision to make.

## Data Path

No new database table is required in v1. Queue items are stored as:

- `task_requests.task_type = ray_review_item`
- `payload.review_queue = true`
- `payload.decision_type`
- `payload.ray_decision_required = true`
- `payload.source_table/source_id`
- `payload.options/pros/cons/risk_notes`

## Commands

```bash
python3 scripts/review/build_ray_review_queue.py --dry-run --limit 25 --no-external-ai --json
python3 scripts/review/generate_ray_review_report.py --dry-run --limit 10 --no-external-ai --json
python3 scripts/review/capture_ray_decision.py --dry-run --review-id "sample-review-id" --decision "changes_requested" --feedback "Make this more focused on business funding leads." --no-external-ai --json
```

## Safety

The queue builder and decision capture scripts never publish, send, trade, deploy, start schedulers, call external AI, or approve/reject the underlying risky action.
