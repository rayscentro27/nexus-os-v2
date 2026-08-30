# WP6.5 Telegram Integration Repair

## Scope

This checkpoint repairs the shared Telegram department-routing and verified-result
rendering path under the approved WP6.5 gate. It does not certify the four new
live retests; those require fresh messages from Ray after this checkpoint.

## Preserved pre-repair evidence

The four real responses remain historical FAILED/PARTIAL evidence. They are not
rewritten or upgraded: daily operations returned a legacy 19-process summary,
repository intelligence returned generic Git status, Ray Review failed to route,
and system health was routed to the daily operations path.

## Root causes

1. `classify_intent()` tested the broad state-query set before Ray Review, so
   “what items currently need my review” was not an execution request.
2. Health and daily operations shared the legacy daily-monitor adapter and
   renderer, whose payload lacked live per-service/operator health detail and
   contained a stale paused-policy sentence.
3. Repo execution discarded the incoming question and only produced generic
   worktree metadata; no question-specific Active Operator history evidence was
   generated.
4. Ray Review created a generic placeholder instead of reading and prioritizing
   the current governed review queue.

## Repair

- Health terms now resolve before general operations and use a distinct live
  governed health adapter.
- Daily results include current telemetry classifications, operator heartbeat
  state/policy, stale evidence, and bounded recommendations.
- Repo context preserves the user question and produces up to three real
  path-scoped Git-history findings for Active Operator stability requests.
- Ray Review reads current approval cards, sorts by risk, and renders item,
  reason, recommendation, consequence, and first-review priority.
- Execution metadata identifies the execution lane; no authority boundary,
  receipt, or fail-closed behavior was weakened.

## Fresh retest status

`FRESH_TELEGRAM_RETEST_REQUIRED=YES`. No Telegram poll, injected update, or
manual production route invocation was used for certification in this repair.

## Round 2 repair

The next real responses exposed five remaining defects. Review questions now
recognize natural “which/what items require review” wording and resolve to the
governed Ray Review route. Daily Operations now uses the canonical daily adapter
and reports named Hermes, Ollama, SearXNG, TruthKernel, Active Operator, and
Mac/Oracle bridge states from explicit evidence. Generic stale next actions are
suppressed. System Health retains a distinct health route and reports named
service states separately from legacy process-registry telemetry. Repository
findings now explain operational consequences based on the actual changed paths.

This remains a development checkpoint only. The four new real Telegram
responses are required before any communication or loop certification changes.

## Security and boundaries

TruthKernel remains authoritative. No credentials were printed or changed, no
external consequential action was performed, and Active Operator remains
paused under the existing campaign policy.
