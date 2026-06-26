# Nexus Hermes Decision Memory

Hermes decision memory stores safe internal summaries of Ray's preferences, repeated decisions, recommendations, and outcomes.

## Memory Types

- preferred topics
- rejected ideas
- winning angles
- preferred formats
- prioritized offers
- scoring adjustments
- repeated recommendations
- successful experiments
- paper-only trading strategy patterns
- compliance concerns
- Ray feedback

## Storage Model

The TypeScript model is defined in `src/config/hermesDecisionMemory.ts`.

The current safe write path is:

- dry-run report by default
- optional live internal `task_requests` row with `task_type=hermes_decision_memory`
- optional `nexus_events` proof with `action=ray_feedback_captured`

No raw private customer data, credentials, broker data, cookies, or tokens should be stored in memory.

## Recommendation History

Hermes recommendation history tracks:

- recommendation
- rationale
- linked report or project
- Ray decision
- outcome summary

This lets Hermes prioritize patterns Ray repeatedly approves and downgrade ideas Ray repeatedly rejects.

## Command

```bash
python3 scripts/research/capture_ray_feedback.py --dry-run --feedback "Prioritize business funding videos that can become GoClear SEO content." --no-external-ai --json
```
